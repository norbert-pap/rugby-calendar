"""Optional viewing hints. Provider listings advertise channels, not playback proof.

Only DESCRIPTION and revision timestamps change; SEQUENCE remains upstream-owned.
No provider URL, credentials or arbitrary catalogue text reaches public output.
"""
import json
import os
import queue
import threading
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BEGIN = '[Sports calendar viewing]'
END = '[/Sports calendar viewing]'
MAX_BYTES = 64_000_000
MAX_RECORDS = 150_000
LOOKUP_SECONDS = 45
ALIASES = {'exeter chiefs': 'exeter', 'harlequins': 'harlequins'}
EXCLUDED = re.compile(r"\b(women|womens|w|wxv|ladies|girls|boys|youth|academy|reserves|development|2nd xv|second xv|a xv|b xv|a team|b team|u\s?\d{2}s?|under\s?\d{2}|cancelled|canceled)\b")


def normal(value):
    value = unicodedata.normalize('NFKC', str(value)).casefold()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def fetch_listings(config):
    """Two bounded Xtream live-catalogue reads; callers suppress all exceptions."""
    base = config['url'].rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('Invalid provider configuration')
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = build_opener(NoRedirect)
    result = []
    for action in ('get_live_categories', 'get_live_streams'):
        query = urlencode({'username': config['username'], 'password': config['password'], 'action': action})
        request = Request(base + '/player_api.php?' + query, headers={'User-Agent': 'SportsCalendar/1.0'})
        with opener.open(request, timeout=15) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Oversized provider response')
        records = json.loads(body)
        if not isinstance(records, list) or len(records) > MAX_RECORDS or any(not isinstance(r, dict) for r in records):
            raise ValueError('Invalid provider response')
        result.append(records)
    return tuple(result)


def lookup_with_deadline(config):
    """Bound the complete lookup, including slow headers and trickling bodies."""
    result = queue.Queue(maxsize=1)
    def worker():
        try:
            value = fetch_listings(config)
        except Exception:
            value = None  # Never transport or print authenticated exceptions.
        result.put(value)
    threading.Thread(target=worker, name='calendar-provider', daemon=True).start()
    try:
        value = result.get(timeout=LOOKUP_SECONDS)
    except queue.Empty:
        raise TimeoutError('Provider lookup deadline exceeded') from None
    if value is None:
        raise ValueError('Provider unavailable')
    return value


def eligible(group, name):
    group = normal(group)
    exact = {'au stan ppv', 'uk florugby ppv', 'uk pdc board ppv',
             'uk sport raw', 'uk sport hd', 'nz sky sport raw',
             'hu hungary hd 4k', 'hu hungary', 'us sport hd raw 60fps',
             'us sport hd', 'us sport raw'}
    return group in exact or (group.startswith('uk sport ') and re.search(r'\b(premier|viaplay)\b', normal(name)) is not None)


def listing_date(name):
    # Accept only unambiguous year-first dates. Multiple dates are ambiguous.
    matches = re.findall(r'(?<!\d)(20\d{2})[-/](\d{2})[-/](\d{2})(?!\d)', name)
    if len(matches) != 1:
        return None
    try:
        return datetime(*(int(x) for x in matches[0])).date()
    except ValueError:
        return None


def label_for(name):
    # Public output is generated only from these channel tokens, never raw names.
    patterns = (
        (r'\bstan\s*(\d{1,2})\b', 'STAN {}'),
        (r'\bflorugby\s*(\d{1,2})\b', 'FloRugby {}'),
        (r'\bpdc\s*(?:board\s*)?(\d{1,2})\b', 'PDC Board {}'),
        (r'\bsky\s*sports?\s*(\d{1,2})\b', 'Sky Sport {}'),
        (r'\btnt\s*sports?\s*(\d{1,2})\b', 'TNT Sports {}'),
        (r'\bpremier\s*sports?\s*(\d{1,2})\b', 'Premier Sports {}'),
        (r'\bviaplay\s*(\d{1,2})\b', 'Viaplay {}'),
        (r'\bm\s*(4)\s*sport\b', 'M{} Sport'),
    )
    for pattern, template in patterns:
        found = re.search(pattern, normal(name))
        if found:
            return template.format(int(found[1]))
    for token, label in [('sky sports main event', 'Sky Sports Main Event'), ('sky sports action', 'Sky Sports Action'), ('sky sports arena', 'Sky Sports Arena'), ('eurosport 1', 'Eurosport 1'), ('eurosport 2', 'Eurosport 2')]:
        if contains(normal(name), token):
            return label
    return None


def contains(text, phrase):
    return re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text) is not None


def matches(name, terms):
    if len(terms) == 1:
        return contains(name, terms[0])
    for full, alias in ALIASES.items():
        name = re.sub(r'(?<!\w)' + re.escape(full) + r'(?!\w)', alias, name)
    return any(contains(name, first + ' ' + separator + ' ' + second)
               for first, second in (terms, terms[::-1])
               for separator in ('v', 'vs', 'versus'))


def event_query(event):
    title = str(event.get('SUMMARY', ''))
    # Club prefixes are presentation added by merge.py.
    title = re.sub(r'^(?:Harlequins|Hurricanes):\s*', '', title)
    teams = re.split(r'\s+(?:vs?\.?|versus)\s+', title, flags=re.I)
    if len(teams) == 2:
        teams = [ALIASES.get(normal(t), normal(t)) for t in teams]
        if all(teams) and teams[0] != teams[1]:
            return teams, teams[0].title()
        return None
    # For sessions/stages require the complete supplied title, not tournament
    # family substrings that could select an unrelated session.
    title = normal(title)
    if len(title) < 12:
        return None
    return [title], str(event.get('SUMMARY'))


def source_hints(title, description):
    text = normal(title + ' ' + description)
    hints = []
    for phrase, label in [('sky sports', 'Sky Sports (UK)'), ('tnt sports', 'TNT Sports (UK)'), ('itv4', 'ITV4 (UK)'), ('itv', 'ITV (UK)'), ('eurosport', 'Eurosport')]:
        if contains(text, phrase):
            hints.append('Broadcaster: ' + label)
    return hints


def sport_context(sport, name, group):
    if sport == 'rugby':
        phrases = ('rugby', 'six nations', 'nations championship',
                   'bledisloe', 'lions', 'urc')
        return any(contains(name, phrase) for phrase in phrases)
    if sport == 'darts':
        return normal(group) == 'uk pdc board ppv' or any(contains(name, p) for p in ('darts', 'pdc'))
    if sport == 'cycling':
        return any(contains(name, p) for p in ('cycling', 'giro d italia', 'tour de france',
                   'vuelta a espana', 'milan san remo', 'tour of flanders',
                   'paris roubaix', 'liege bastogne liege', 'il lombardia'))
    return False


def enrich(calendar, now, sport=None):
    stats = {'provider': 'unconfigured', 'matched_events': 0, 'hinted_events': 0}
    if sport is None:
        calendar_name = normal(calendar.get('X-WR-CALNAME', ''))
        sport = next((s for s in ('rugby', 'cycling', 'darts') if contains(calendar_name, s)), None)
    records = []
    raw = os.environ.get('WATCH_PROVIDER_JSON', '')
    if raw:
        try:
            config = json.loads(raw)
            if not isinstance(config, dict) or any(not isinstance(config.get(k), str) or not config[k] for k in ('url', 'username', 'password')):
                raise ValueError('Invalid provider configuration')
            categories, streams = lookup_with_deadline(config)
            groups = {str(c.get('category_id')): c.get('category_name', '') for c in categories}
            for stream in streams:
                name = str(stream.get('name', ''))
                if len(name) > 1000 or '://' in name or '♀' in name or EXCLUDED.search(normal(name)):
                    continue
                group = groups.get(str(stream.get('category_id')), '')
                normalized = normal(name)
                if re.search(r'\b(replay|highlights?|re run|rerun|classic|vod)\b', normalized):
                    continue
                if not eligible(group, name) or not sport_context(sport, normalized, group):
                    continue
                day, label = listing_date(name), label_for(name)
                if day and label:
                    records.append((normal(name), day, label))
            stats['provider'] = 'available'
        except Exception:
            # Exceptions may contain authenticated request URLs. Never log them.
            records = []
            stats['provider'] = 'unavailable'
    for event in calendar.walk('VEVENT'):
        original = str(event.get('DESCRIPTION', ''))
        # Replace only our complete trailing block; source prose is untouched.
        description = re.sub(r'(?:\n\n)?' + re.escape(BEGIN) + r'\n.*?\n' + re.escape(END) + r'\Z', '', original, flags=re.S)
        lines = []
        if str(event.get('STATUS', '')).upper() != 'CANCELLED':
            lines = source_hints(str(event.get('SUMMARY', '')), description)
            start = event.decoded('DTSTART') if event.get('DTSTART') else None
            end = event.decoded('DTEND') if event.get('DTEND') else start
            query = event_query(event)
            if isinstance(start, datetime) and isinstance(end, datetime) and timedelta(0) <= end - start <= timedelta(days=1) and query and not EXCLUDED.search(normal(event.get('SUMMARY', ''))):
                terms, search = query
                labels = sorted({label for name, day, label in records
                                 if abs((day - start.date()).days) <= 1 and matches(name, terms)})
                if labels:
                    lines = ['Watch on: ' + ', '.join(labels), 'UHF: search ' + search,
                             'Channel listing checked: ' + now.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')] + lines
                    stats['matched_events'] += 1
            if lines:
                stats['hinted_events'] += 1
        updated = description + ('\n\n' if description and lines else '') + (BEGIN + '\n' + '\n'.join(lines) + '\n' + END if lines else '')
        if updated != original:
            for stamp in ('DTSTAMP', 'LAST-MODIFIED'):
                if stamp in event:
                    del event[stamp]
                event.add(stamp, now)
            if updated:
                event['DESCRIPTION'] = updated
            elif 'DESCRIPTION' in event:
                del event['DESCRIPTION']
    return stats
