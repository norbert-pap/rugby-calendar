#!/usr/bin/env python3
"""Build the combined public rugby subscription; never publish a partial fetch."""
import argparse
import copy
import json
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from icalendar import Calendar
import watch

BASE = 'https://api.gainline.app/calendar/'
SOURCES = [
    ('Harlequins', 'Harlequins', 'team/5-harlequins'),
    ('Hurricanes (NZ)', 'Hurricanes', 'team/79-hurricanes'),
    ('Six Nations', None, 'league/3-six-nations'),
    ('The Rugby Championship', None, 'league/2-rugby-championship'),
    ('International Friendlies', None, 'league/4-internationals'),
    ('Rugby World Cup', None, 'league/16-world-cup'),
    ('Nations Championship', None, 'league/30-nations-championship'),
    ('The Lions Series', None, 'league/9-lions-tour'),
    ('Pacific Nations Cup', None, 'league/28-pacific-nations-cup'),
    ('Rugby Europe Championship', None, 'league/24-rugby-europe-championship'),
]
# A source that fails to download is served from its last good copy for this long.
MAX_STALE = timedelta(days=7)
RUN_ID = str(uuid.uuid4())


def log(event, **fields):
    print(json.dumps({'event': event, 'run_id': RUN_ID, **fields}), flush=True)


def as_utc(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, timezone.utc)
    raise ValueError('Invalid calendar date')


def fetch(source):
    name, label, path = source
    result = subprocess.run([
        'curl', '--fail', '--location', '--silent', '--show-error',
        '--connect-timeout', '15', '--max-time', '45',
        '--retry', '2', '--retry-delay', '2', BASE + path,
    ], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f'{name}: fetch failed: {result.stderr.decode(errors="replace").strip()}')
    if len(result.stdout) > 5_000_000:
        raise ValueError(f'{name}: oversized source')
    return name, label, result.stdout


def combine(feeds, now):
    now = as_utc(now)
    cutoff = now - timedelta(days=30)
    calendar = Calendar()
    calendar.add('PRODID', '-//Rugby Calendar//Gainline combined fixtures//EN')
    calendar.add('VERSION', '2.0')
    calendar.add('CALSCALE', 'GREGORIAN')
    calendar.add('METHOD', 'PUBLISH')
    calendar.add('X-WR-CALNAME', 'Rugby')
    calendar.add('X-WR-CALDESC', 'Harlequins, Hurricanes (NZ), and men\'s senior internationals. Public fixtures from Gainline.')
    calendar.add('X-WR-TIMEZONE', 'Europe/Budapest')
    calendar.add('X-PUBLISHED-TTL', 'PT6H')
    calendar.add('REFRESH-INTERVAL', timedelta(hours=6), parameters={'VALUE': 'DURATION'})
    calendar.add('X-LAST-REFRESHED', now.strftime('%Y%m%dT%H%M%SZ'))
    records = {}
    zones = {}
    stats = {'sources': [], 'duplicates_removed': 0, 'old_events_removed': 0}
    for name, label, body in feeds:
        if not body.lstrip().startswith(b'BEGIN:VCALENDAR') or not body.rstrip().endswith(b'END:VCALENDAR'):
            raise ValueError(f'{name}: not a complete iCalendar document')
        try:
            parsed = Calendar.from_ical(body)
        except Exception as exc:
            raise ValueError(f'{name}: invalid iCalendar') from exc
        if parsed.name != 'VCALENDAR' or str(parsed.get('VERSION')) != '2.0':
            raise ValueError(f'{name}: invalid calendar version')
        for component in parsed.walk():
            if component.errors:
                raise ValueError(f'{name}: calendar parsing errors: {component.errors}')
        for zone in parsed.walk('VTIMEZONE'):
            zones[str(zone['TZID'])] = zone
        events = parsed.walk('VEVENT')
        stats['sources'].append({'name': name, 'events': len(events)})
        for event in events:
            if not event.get('UID') or not event.get('DTSTART') or not event.get('DTSTAMP'):
                raise ValueError(f'{name}: event missing UID, DTSTART or DTSTAMP')
            start = as_utc(event.decoded('DTSTART'))
            end = as_utc(event.decoded('DTEND')) if event.get('DTEND') else start
            if end < cutoff:
                stats['old_events_removed'] += 1
                continue
            recurrence = str(event.get('RECURRENCE-ID', ''))
            key = (str(event['UID']), recurrence)
            modified = as_utc(event.decoded('LAST-MODIFIED') if event.get('LAST-MODIFIED') else event.decoded('DTSTAMP'))
            if key in records:
                stats['duplicates_removed'] += 1
                if records[key][0] >= modified:
                    continue
            event = copy.deepcopy(event)
            for stamp in ('DTSTAMP', 'LAST-MODIFIED', 'CREATED'):
                if event.get(stamp):
                    normalized = as_utc(event.decoded(stamp))
                    del event[stamp]
                    event.add(stamp, normalized)
            if label:
                event['SUMMARY'] = f'{label}: {event.get("SUMMARY", "Fixture")}'
            records[key] = (modified, start, event)
    for _, zone in sorted(zones.items()):
        calendar.add_component(zone)
    for _, _, event in sorted(records.values(), key=lambda item: (item[1], str(item[2]['UID']))):
        calendar.add_component(event)
    stats['events'] = len(records)
    stats['last_successful_refresh'] = now.isoformat()
    return calendar, stats


def atomic_write(path, body):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(body)
    os.replace(temp, path)


def cache_path(output, source):
    return output.parent / 'sources' / (source[2].replace('/', '-') + '.ics')


def fetch_or_cached(output, source, fetched_at, now):
    """Fetch a source, falling back to its last good copy if it is under MAX_STALE old."""
    try:
        return fetch(source) + (now,)
    except RuntimeError as exc:
        cached, last = cache_path(output, source), fetched_at.get(source[0])
        if not cached.exists() or not last or now - datetime.fromisoformat(last) > MAX_STALE:
            raise
        log('source_stale', name=source[0], error=str(exc), fetched_at=last)
        return source[0], source[1], cached.read_bytes(), datetime.fromisoformat(last)


def refresh(output, now=None):
    now = now or datetime.now(timezone.utc)
    status = output.with_name('status.json')
    previous = json.loads(status.read_text()) if status.exists() else {}
    fetched_at = {source['name']: source.get('fetched_at') for source in previous.get('sources', [])}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda source: fetch_or_cached(output, source, fetched_at, now), SOURCES))
    feeds = [result[:3] for result in results]
    calendar, stats = combine(feeds, now)
    for source, result in zip(stats['sources'], results):
        source['fetched_at'] = result[3].isoformat()
        source['stale'] = result[3] != now
    stats['watch'] = watch.enrich(calendar, now, sport='rugby')
    payload = calendar.to_ical()
    if len(payload) >= 1_000_000:
        raise ValueError('Combined calendar exceeds Proton subscription size limit')
    # Re-parse before replacing the public file.
    if len(Calendar.from_ical(payload).walk('VEVENT')) != stats['events']:
        raise ValueError('Output validation failed')
    output.parent.mkdir(parents=True, exist_ok=True)
    for source, result in zip(SOURCES, results):
        if result[3] == now:
            cache_path(output, source).parent.mkdir(exist_ok=True)
            atomic_write(cache_path(output, source), result[2])
    atomic_write(output, payload)
    atomic_write(status, (json.dumps(stats, indent=2) + '\n').encode())
    for source in stats['sources']:
        log('source_validated', **source)
    log('calendar_refreshed', events=stats['events'], bytes=len(payload), duplicates_removed=stats['duplicates_removed'], old_events_removed=stats['old_events_removed'], watch=stats['watch'])
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('rugby.ics'))
    args = parser.parse_args()
    try:
        refresh(args.output)
    except Exception as exc:
        log('refresh_failed', error=str(exc))
        raise
