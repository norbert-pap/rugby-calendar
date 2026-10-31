import copy
import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch
from icalendar import Calendar, Event
import watch

NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
CATEGORIES = [{'category_id': '1', 'category_name': 'AU| STAN PPV'}]
LISTING = {'category_id': '1', 'name': 'AU| STAN 12: Exeter v Harlequins PREM Rugby (2026-11-01 01:55:50)'}
CONFIG = json.dumps({'url': 'https://private.invalid', 'username': 'SECRET_USER', 'password': 'SECRET_PASS'})


def fixture(title='Harlequins: Exeter Chiefs vs Harlequins', start=None):
    cal, event = Calendar(), Event()
    cal.add('X-WR-CALNAME', 'Darts' if title.startswith('World Grand Prix') else 'Rugby')
    event.add('uid', 'original-uid')
    event.add('summary', title)
    event.add('dtstart', start or datetime(2026, 10, 31, 15, tzinfo=timezone.utc))
    event.add('dtend', (start or datetime(2026, 10, 31, 15, tzinfo=timezone.utc)) + timedelta(hours=2))
    event.add('dtstamp', NOW)
    event.add('sequence', 2)
    event.add('description', 'Original source text\nUntouched detail.')
    cal.add_component(event)
    return cal, event


class WatchTests(unittest.TestCase):
    def test_exeter_adjacent_provider_date_preserves_fixture(self):
        cal, event = fixture()
        original = copy.deepcopy(event)
        with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch('watch.fetch_listings', return_value=(CATEGORIES, [LISTING]), create=True):
            stats = watch.enrich(cal, NOW)
        self.assertIn('Watch on: STAN 12', str(event['DESCRIPTION']))
        self.assertIn('UHF: search Exeter', str(event['DESCRIPTION']))
        self.assertTrue(str(event['DESCRIPTION']).startswith(str(original['DESCRIPTION'])))
        for key in ('UID', 'SUMMARY', 'DTSTART', 'DTEND', 'DTSTAMP', 'SEQUENCE'):
            self.assertEqual(event[key], original[key])
        self.assertEqual(stats['matched_events'], 1)

    def enrich_with(self, event_title=None, listing_name=None, group='AU| STAN PPV', status=None, start=None):
        cal, event = fixture(event_title or 'Harlequins: Exeter Chiefs vs Harlequins', start)
        if status:
            event['STATUS'] = status
        listing = {**LISTING, 'name': listing_name or LISTING['name']}
        with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'fetch_listings', return_value=([{'category_id': '1', 'category_name': group}], [listing])):
            stats = watch.enrich(cal, NOW)
        return cal, event, stats

    def test_actual_listing_format(self):
        _, event, _ = self.enrich_with(listing_name='AU (STAN 12) | Exeter v Harlequins  PREM Rugby Round 5 2026/27 (2026-11-01 01:55:50)')
        self.assertIn('Watch on: STAN 12', str(event['DESCRIPTION']))

    def test_rejects_wrong_stale_undated_ambiguous_and_excluded_listings(self):
        for name in [
            'STAN 12 Exeter v Bath 2026-11-01',
            'STAN 12 Exeter v Harlequins 2026-11-03',
            'STAN 12 Exeter v Harlequins',
            'STAN 12 Exeter v Harlequins 01/11/2026',
            'STAN 12 Exeter v Harlequins 2026-10-31 2026-11-01',
            'STAN 12 Exeter v Harlequins Women 2026-11-01',
            'STAN 12 Exeter v Harlequins U20 2026-11-01',
            'STAN 12 Exeter v Harlequins Academy 2026-11-01',
            'STAN 12 Exeter v Harlequins WXV 2026-11-01',
            'STAN 12 Exeter v Harlequins ♀ 2026-11-01',
            'STAN 12 Exeter v Harlequins U20s 2026-11-01',
            'STAN 12 Exeter v Harlequins CANCELLED 2026-11-01',
            'STAN 12 Exeter v Harlequinshire 2026-11-01',
            'STAN 12 Exeter v Bath; Harlequins v Sale 2026-11-01',
        ]:
            with self.subTest(name=name):
                _, event, stats = self.enrich_with(listing_name=name + ' Rugby')
                self.assertNotIn('Watch on:', str(event['DESCRIPTION']))
                self.assertEqual(stats['matched_events'], 0)

    def test_cancelled_and_all_day_spans_have_no_dynamic_channel(self):
        for kwargs in [{'status': 'CANCELLED'}, {'start': date(2026, 10, 31)}]:
            _, event, _ = self.enrich_with(**kwargs)
            self.assertNotIn('Watch on:', str(event['DESCRIPTION']))

    def test_only_imported_categories_qualify(self):
        for group in ['US| STAN PPV', 'AU| OTHER', 'UK| SPORT 4K', 'UK| SPORT LOW', 'AU| STAN PPV EXTRA']:
            with self.subTest(group=group):
                _, event, _ = self.enrich_with(group=group)
                self.assertNotIn('Watch on:', str(event['DESCRIPTION']))
        for group in ['AU| STAN PPV', 'UK| SPORT ᴿᴬᵂ', 'UK| SPORT ᴴᴰ', 'NZ| SKY SPORT ᴿᴬᵂ', 'HU| HUNGARY HD/4K', 'US| SPORT ᴴᴰ/ᴿᴬᵂ ⁶⁰ᶠᵖˢ']:
            with self.subTest(group=group):
                _, event, _ = self.enrich_with(group=group)
                self.assertIn('Watch on:', str(event['DESCRIPTION']))

    def test_idempotence_and_outage_removes_stale_owned_block(self):
        cal, event, _ = self.enrich_with()
        once = cal.to_ical()
        with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'fetch_listings', return_value=(CATEGORIES, [LISTING])):
            watch.enrich(cal, NOW)
        self.assertEqual(cal.to_ical(), once)
        with patch.dict(os.environ, {}, clear=True):
            watch.enrich(cal, NOW)
        self.assertEqual(str(event['DESCRIPTION']), 'Original source text\nUntouched detail.')

    def test_missing_credentials_keeps_generic_source_hint(self):
        cal, event = fixture('World Grand Prix: Final (Sky Sports)')
        with patch.dict(os.environ, {}, clear=True), patch.object(watch, 'fetch_listings') as fetch:
            stats = watch.enrich(cal, NOW)
        fetch.assert_not_called()
        self.assertIn('Broadcaster: Sky Sports (UK)', str(event['DESCRIPTION']))
        self.assertNotIn('Watch on:', str(event['DESCRIPTION']))
        self.assertEqual(stats['provider'], 'unconfigured')

    def test_provider_failures_and_invalid_config_never_expose_secrets(self):
        for config in [CONFIG, 'bad SECRET_PASS', '{}']:
            cal, event = fixture()
            with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': config}), patch.object(watch, 'fetch_listings', side_effect=RuntimeError('https://private.invalid?password=SECRET_PASS')), patch('sys.stdout', new_callable=io.StringIO) as output, patch('sys.stderr', new_callable=io.StringIO) as error:
                stats = watch.enrich(cal, NOW)
            public = cal.to_ical().decode() + json.dumps(stats) + output.getvalue() + error.getvalue()
            self.assertNotIn('SECRET_', public)
            self.assertNotIn('private.invalid', public)
            self.assertEqual(stats['provider'], 'unavailable')

    def test_non_team_event_needs_complete_session_title(self):
        _, event, _ = self.enrich_with(event_title='World Grand Prix: Final', listing_name='PDC Board 1 World Grand Prix: Semi Final 2026-10-31', group='UK| PDC BOARD PPV')
        self.assertNotIn('Watch on:', str(event['DESCRIPTION']))
        _, event, _ = self.enrich_with(event_title='World Grand Prix: Final', listing_name='PDC Board 1 World Grand Prix: Final 2026-10-31', group='UK| PDC BOARD PPV')
        self.assertIn('Watch on: PDC Board 1', str(event['DESCRIPTION']))

    def test_provider_reads_bounded_and_redirects_disabled(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                self.size = size
                return b'[]'
        response = Response()
        with patch('watch.build_opener') as build:
            build.return_value.open.return_value = response
            self.assertEqual(watch.fetch_listings(json.loads(CONFIG)), ([], []))
        self.assertEqual(response.size, watch.MAX_BYTES + 1)
        self.assertEqual(build.return_value.open.call_count, 2)
        self.assertEqual(build.return_value.open.call_args.kwargs['timeout'], 15)
        self.assertIsNone(build.call_args.args[0].redirect_request(None, None, None, None, None, None))

    def test_changed_description_updates_revision_metadata_only(self):
        cal, event = fixture('World Grand Prix (Sky Sports)')
        old = NOW - timedelta(days=3)
        del event['DTSTAMP']
        event.add('dtstamp', old)
        event.add('last-modified', old)
        with patch.dict(os.environ, {}, clear=True):
            watch.enrich(cal, NOW)
        self.assertEqual(event.decoded('DTSTAMP'), NOW)
        self.assertEqual(event.decoded('LAST-MODIFIED'), NOW)
        self.assertEqual(event['SEQUENCE'], 2)
        with patch.dict(os.environ, {}, clear=True):
            watch.enrich(cal, NOW + timedelta(hours=1))
        self.assertEqual(event.decoded('LAST-MODIFIED'), NOW)

    def test_publishers_enrich_once_before_serialization(self):
        import tempfile
        from pathlib import Path
        import merge
        import sports
        from test_merge import feed
        with tempfile.TemporaryDirectory() as folder, patch.object(merge, 'SOURCES', [('Test', None, 'test')]), patch.object(merge, 'fetch', return_value=('Test', None, feed(start='20261031T150000Z'))), patch.object(watch, 'enrich', return_value={'provider': 'unconfigured', 'matched_events': 0, 'hinted_events': 0}) as enrich:
            merge.refresh(Path(folder) / 'rugby.ics', NOW)
            enrich.assert_called_once()
        from test_sports import feed as sports_feed
        with tempfile.TemporaryDirectory() as folder, patch.object(sports, 'download', return_value=sports_feed('World Grand Prix (Sky Sports)')), patch.object(watch, 'enrich', return_value={'provider': 'unconfigured', 'matched_events': 0, 'hinted_events': 0}) as enrich:
            sports.refresh('darts', Path(folder), NOW)
            enrich.assert_called_once()

    def test_oversized_or_malformed_catalogue_is_optional(self):
        for body in [b'x' * 101, b'{"error":"SECRET_PASS"}', b'not json']:
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, size): return body
            cal, _ = fixture()
            with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'MAX_BYTES', 100), patch.object(watch, 'build_opener') as build:
                build.return_value.open.return_value = Response()
                stats = watch.enrich(cal, NOW)
            self.assertEqual(stats['provider'], 'unavailable')
            self.assertNotIn('SECRET_PASS', cal.to_ical().decode() + json.dumps(stats))

    def test_reversed_teams_and_full_alias_work(self):
        _, event, _ = self.enrich_with(listing_name='AU (STAN 12) Harlequins vs Exeter Chiefs PREM Rugby 2026-10-31')
        self.assertIn('Watch on: STAN 12', str(event['DESCRIPTION']))

    def test_exact_imported_premier_exception(self):
        self.assertTrue(watch.eligible('UK| SPORT 4K', 'Premier Sports 1'))
        self.assertTrue(watch.eligible('UK| SPORT LOW', 'Viaplay 1'))
        self.assertFalse(watch.eligible('UK| SPORT 4K', 'Sky Sports 1'))
        self.assertFalse(watch.eligible('FR| SPORT 4K', 'Premier Sports 1'))

    def test_same_opponents_other_sport_and_replays_are_rejected(self):
        for title in [
            'STAN 12 France v England UEFA Nations League 2026-10-31',
            'STAN 12 France v England Rugby replay 2026-10-31',
            'STAN 12 France v England Rugby highlights 2026-10-31',
            'STAN 12 France v England Classic Rugby 2026-10-31',
            'STAN 12 France v England Rugby re-run 2026-10-31',
            'STAN 12 France v England Rugby VOD 2026-10-31',
            'STAN 12 France v England 2026-10-31',
        ]:
            with self.subTest(title=title):
                _, event, _ = self.enrich_with(event_title='France vs England', listing_name=title)
                self.assertNotIn('Watch on:', str(event['DESCRIPTION']))

    def test_competition_provides_positive_rugby_context(self):
        _, event, _ = self.enrich_with(event_title='Ireland vs Argentina', listing_name='AU (STAN 62) | Ireland v Argentina Nations Championship Round 4 2026 (2026-11-01 07:00:50)')
        self.assertIn('Watch on: STAN 62', str(event['DESCRIPTION']))

    def test_second_and_development_teams_are_rejected(self):
        for qualifier in ('2nd XV', 'second XV', 'A XV', 'B team'):
            with self.subTest(qualifier=qualifier):
                _, event, _ = self.enrich_with(listing_name='STAN 12 Exeter v Harlequins ' + qualifier + ' Rugby 2026-10-31')
                self.assertNotIn('Watch on:', str(event['DESCRIPTION']))

    def test_catalogue_deadline_is_optional_and_worker_is_daemon(self):
        import threading
        gate = threading.Event()
        cal, _ = fixture()
        def slow_fetch(config):
            gate.wait(2)
            return CATEGORIES, [LISTING]
        try:
            with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'fetch_listings', side_effect=slow_fetch), patch.object(watch, 'LOOKUP_SECONDS', 0.01, create=True):
                stats = watch.enrich(cal, NOW)
                self.assertEqual(stats['provider'], 'unavailable')
                workers = [t for t in threading.enumerate() if t.name == 'calendar-provider']
                self.assertTrue(workers)
                self.assertTrue(all(t.daemon for t in workers))
        finally:
            gate.set()

    def test_same_session_title_requires_correct_sport_context(self):
        _, event, _ = self.enrich_with(event_title='World Grand Prix: Final', listing_name='STAN 12 World Grand Prix: Final Football 2026-10-31')
        self.assertNotIn('Watch on:', str(event['DESCRIPTION']))

    def test_cycling_title_and_unknown_calendar(self):
        cal, event = fixture('Tour de France 2026 Stage 1')
        cal['X-WR-CALNAME'] = 'Cycling — Grand Tours & Monuments'
        listing = {**LISTING, 'name': 'Eurosport 1 Tour de France 2026 Stage 1 2026-10-31'}
        with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'fetch_listings', return_value=([{'category_id': '1', 'category_name': 'UK| SPORT ᴴᴰ'}], [listing])):
            watch.enrich(cal, NOW)
        self.assertIn('Watch on: Eurosport 1', str(event['DESCRIPTION']))
        cal, event = fixture()
        del cal['X-WR-CALNAME']
        with patch.dict(os.environ, {'WATCH_PROVIDER_JSON': CONFIG}), patch.object(watch, 'fetch_listings', return_value=(CATEGORIES, [LISTING])):
            watch.enrich(cal, NOW)
        self.assertNotIn('Watch on:', str(event['DESCRIPTION']))
