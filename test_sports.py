import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch
from icalendar import Calendar, Event
import sports

NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)

def feed(*titles):
    cal = Calendar()
    cal.add('VERSION', '2.0')
    cal.add('PRODID', '-//Tests//EN')
    for i, title in enumerate(titles):
        e = Event()
        e.add('UID', f'{i}@test')
        e.add('DTSTAMP', NOW)
        e.add('DTSTART', date(2027, 5, 8))
        e.add('DTEND', date(2027, 5, 9))
        e.add('SUMMARY', title)
        cal.add_component(e)
    return cal.to_ical()

class SportsTests(unittest.TestCase):
    def test_cycling_exact_mens_scope_and_translation(self):
        body = feed('Giro de Italia 2027 · Etapa 1 [2.UWT]',
                    'Giro de Italia femenino 2027 [2.WWT ♀]',
                    'París-Roubaix 2027 [1.UWT]', 'París-Roubaix femenina 2027 [1.WWT ♀]',
                    'Strade Bianche 2027 [1.UWT]', 'Il Lombardia sub23 2027 [1.2U]')
        c, families = sports.filter_feed('cycling', body)
        self.assertEqual([str(e['SUMMARY']) for e in c.walk('VEVENT')],
                         ["Giro d'Italia 2027 · Stage 1", 'Paris-Roubaix 2027'])
        self.assertEqual(families, {"Giro d'Italia", 'Paris-Roubaix'})
        self.assertEqual(c.walk('VEVENT')[0].decoded('DTSTART'), date(2027, 5, 8))
        self.assertEqual(str(c.walk('VEVENT')[0]['UID']), '0@test')

    def test_all_eight_cycling_families(self):
        titles = [f'{name} 2027 [{category}]' for name, (_, category) in sports.CYCLING.items()]
        _, families = sports.filter_feed('cycling', feed(*titles))
        self.assertEqual(len(families), 8)

    def test_darts_allowlist_includes_sessions_not_exhibitions_or_floor_events(self):
        c, families = sports.filter_feed('darts', feed(
            'World Darts Championship (Sky Sports)',
            'World Darts Championship: Final, 8pm (Sky Sports)',
            'World Cup of Darts (Sky Sports)', 'Players Championship Finals (ITV4)',
            'Players Championship 12', 'Bahrain Darts Masters (ITV4)',
            "Women's World Matchplay (Sky Sports)", 'European Darts Open'))
        self.assertEqual(len(c.walk('VEVENT')), 4)
        self.assertIn('World Cup of Darts', families)

    def test_bad_or_empty_source_rejected(self):
        for body in [b'<html>outage</html>', feed()]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                sports.filter_feed('darts', body)

    def test_no_matches_rejected(self):
        with self.assertRaises(ValueError):
            sports.filter_feed('darts', feed('Players Championship 12'))

    def test_failure_keeps_previous_calendar_and_status(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'darts.ics').write_text('previous calendar')
            (out / 'darts-status.json').write_text('previous status')
            with patch.object(sports, 'download', side_effect=RuntimeError('outage')):
                with self.assertRaises(RuntimeError):
                    sports.refresh('darts', out, NOW)
            self.assertEqual((out / 'darts.ics').read_text(), 'previous calendar')
            self.assertEqual((out / 'darts-status.json').read_text(), 'previous status')

    def test_incomplete_cycling_year_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(sports, 'download', return_value=feed('París-Roubaix 2027 [1.UWT]')):
                with self.assertRaisesRegex(ValueError, 'missing race families'):
                    sports.refresh('cycling', Path(folder), NOW)
            self.assertFalse((Path(folder) / 'cycling.ics').exists())

    def test_next_year_404_keeps_current_year_and_rolls_forward(self):
        titles = [f'{name} 2027 [{category}]' for name, (_, category) in sports.CYCLING.items()]
        later = datetime(2027, 1, 1, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(sports, 'download', side_effect=[feed(*titles), None]) as fetch:
                stats = sports.refresh('cycling', Path(folder), later)
            self.assertIn('2027-wt.ics', fetch.call_args_list[0].args[0])
            self.assertIn('2028-wt.ics', fetch.call_args_list[1].args[0])
            self.assertTrue(fetch.call_args_list[1].kwargs['optional'])
            self.assertEqual(stats['events'], 8)
            self.assertEqual(stats['optional_sources_unpublished'][0]['year'], 2028)
            self.assertTrue((Path(folder) / 'cycling-status.json').exists())

    def test_optional_download_only_tolerates_404(self):
        from urllib.error import HTTPError
        with patch.object(sports, 'urlopen', side_effect=HTTPError('url', 404, 'not found', {}, None)):
            self.assertIsNone(sports.download('https://example.com/feed', optional=True))
            with self.assertRaises(RuntimeError):
                sports.download('https://example.com/feed')
        with patch.object(sports, 'urlopen', side_effect=HTTPError('url', 503, 'outage', {}, None)), patch.object(sports.time, 'sleep'):
            with self.assertRaises(RuntimeError):
                sports.download('https://example.com/feed', optional=True)

    def test_darts_title_uk_clock_removed_but_utc_preserved(self):
        c = Calendar.from_ical(feed('World Grand Prix: Final, 8pm (Sky Sports)'))
        e = c.walk('VEVENT')[0]
        del e['DTSTART']; del e['DTEND']
        e.add('DTSTART', datetime(2027, 10, 3, 19, tzinfo=timezone.utc))
        e.add('DTEND', datetime(2027, 10, 3, 22, tzinfo=timezone.utc))
        selected, _ = sports.filter_feed('darts', c.to_ical())
        e = selected.walk('VEVENT')[0]
        self.assertEqual(str(e['SUMMARY']), 'World Grand Prix: Final (Sky Sports)')
        self.assertEqual(e.decoded('DTSTART').hour, 19)

if __name__ == '__main__':
    unittest.main()
