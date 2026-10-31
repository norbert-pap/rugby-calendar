#!/usr/bin/env python3
"""Publish separate filtered sports subscriptions; retain last-good on source failure."""
import argparse
import copy
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from icalendar import Calendar
import watch
import merge

CYCLING = {
    'Giro de Italia': ("Giro d'Italia", '2.UWT'),
    'Tour de Francia': ('Tour de France', '2.UWT'),
    'La Vuelta': ('Vuelta a España', '2.UWT'),
    'Milán-San Remo': ('Milan-San Remo', '1.UWT'),
    'Tour de Flandes': ('Tour of Flanders', '1.UWT'),
    'París-Roubaix': ('Paris-Roubaix', '1.UWT'),
    'Lieja-Bastoña-Lieja': ('Liège-Bastogne-Liège', '1.UWT'),
    'Il Lombardia': ('Il Lombardia', '1.UWT'),
}
DARTS = {
    'World Darts Championship', 'World Masters', 'Premier League Darts',
    'UK Open', 'World Cup of Darts', 'World Matchplay', 'World Grand Prix',
    'European Championship', 'Grand Slam of Darts', 'Players Championship Finals',
    'World Series of Darts Finals', 'European Open',
}
DARTS_URL = 'https://cswdarts.co.uk/darts-calendar.ics'


def download(url, optional=False):
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'SportsCalendar/1.0'})
            with urlopen(request, timeout=45) as response:
                body = response.read(5_000_001)
            if len(body) > 5_000_000:
                raise ValueError(f'Oversized source: {url}')
            return body
        except HTTPError as exc:
            if optional and exc.code == 404:
                return None
            if exc.code < 500 or attempt == 2:
                raise RuntimeError(f'Source HTTP {exc.code}: {url}') from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError(f'Source unavailable: {url}') from exc
        time.sleep(2)


def filter_feed(sport, body):
    # Validate the whole upstream before dropping anything, including old events.
    validated, _ = merge.combine([('upstream', None, body)], datetime(1900, 1, 1, tzinfo=timezone.utc))
    events = validated.walk('VEVENT')
    if not events:
        raise ValueError('Empty upstream calendar')
    selected = copy.deepcopy(validated)
    selected.subcomponents = [c for c in selected.subcomponents if c.name != 'VEVENT']
    families = set()
    for event in events:
        title = str(event.get('SUMMARY', ''))
        family = None
        if sport == 'cycling':
            for original, (english, category) in CYCLING.items():
                match = re.fullmatch(re.escape(original) + r' (\d{4})( · (?:Etapa \d+|Prólogo))? \[' + re.escape(category) + r'\]', title)
                if match:
                    family = english
                    suffix = (match[2] or '').replace('Etapa', 'Stage').replace('Prólogo', 'Prologue')
                    title = f'{english} {match[1]}{suffix}'
                    break
        else:
            # Match the complete tournament name, optionally followed by session/channel.
            for name in DARTS:
                if re.fullmatch(re.escape(name) + r'(?:: .+)?(?: \([^()]+\))?', title):
                    family = name
                    # Embedded source clock labels are UK time; clients render DTSTART locally.
                    title = re.sub(r', \d{1,2}(?::\d{2})?(?:am|pm)(?= \(|$)', '', title)
                    break
        if family:
            event = copy.deepcopy(event)
            event['SUMMARY'] = title
            selected.add_component(event)
            families.add(family)
    if not families:
        raise ValueError(f'No matching {sport} events; upstream scope may have changed')
    return selected, families


def refresh(sport, folder=Path('.'), now=None):
    now = now or datetime.now(timezone.utc)
    sources = []
    unavailable = []
    if sport == 'cycling':
        for year in (now.year, now.year + 1):
            url = f'https://calendariociclismo.app/feed/{year}-wt.ics'
            body = download(url, optional=year > now.year)
            if body is None:
                unavailable.append({'year': year, 'url': url, 'reason': 'not published (404)'})
                continue
            calendar, families = filter_feed(sport, body)
            missing = {english for english, _ in CYCLING.values()} - families
            if missing:
                raise ValueError(f'{year}: missing race families: {sorted(missing)}')
            sources.append((url, None, calendar.to_ical()))
    else:
        calendar, _ = filter_feed(sport, download(DARTS_URL))
        sources.append((DARTS_URL, None, calendar.to_ical()))
    calendar, stats = merge.combine(sources, now)
    calendar['X-WR-CALNAME'] = 'Cycling — Grand Tours & Monuments' if sport == 'cycling' else 'Darts — Major televised tournaments'
    calendar['X-WR-CALDESC'] = ("Men's Giro d'Italia, Tour de France, Vuelta a España and five Monuments. Source: Calendario Ciclismo."
                              if sport == 'cycling' else 'Major PDC tournaments and published sessions. Source: CSWStats. UK channel labels; local times use DTSTART.')
    calendar['PRODID'] = '-//Sports Calendar//Filtered subscriptions//EN'
    stats['optional_sources_unpublished'] = unavailable
    starts = [merge.as_utc(e.decoded('DTSTART')) for e in calendar.walk('VEVENT')]
    stats['latest_event_start'] = max(starts).isoformat() if starts else None
    stats['watch'] = watch.enrich(calendar, now, sport=sport)
    payload = calendar.to_ical()
    if len(payload) >= 1_000_000:
        raise ValueError('Calendar exceeds Proton subscription size limit')
    if len(Calendar.from_ical(payload).walk('VEVENT')) != stats['events']:
        raise ValueError('Output validation failed')
    status = (json.dumps(stats, indent=2) + '\n').encode()
    folder.mkdir(parents=True, exist_ok=True)
    merge.atomic_write(folder / f'{sport}.ics', payload)
    merge.atomic_write(folder / f'{sport}-status.json', status)
    merge.log('sports_calendar_refreshed', sport=sport, **stats)
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sport', choices=['cycling', 'darts'])
    parser.add_argument('--output-dir', type=Path, default=Path('.'))
    args = parser.parse_args()
    try:
        refresh(args.sport, args.output_dir)
    except Exception as exc:
        merge.log('sports_refresh_failed', sport=args.sport, error=str(exc))
        raise
