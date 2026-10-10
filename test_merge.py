import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from icalendar import Calendar, Event
import merge

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)

def feed(uid='match-1@gainline.app', start='20261017T050000Z', modified='20261001T000000Z', summary='Australia vs New Zealand'):
    return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\nBEGIN:VEVENT\r\n'
            f'UID:{uid}\r\nDTSTAMP:{modified}\r\nLAST-MODIFIED:{modified}\r\nDTSTART:{start}\r\n'
            f'SUMMARY:{summary}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n').encode()

class MergeTests(unittest.TestCase):
    def test_duplicate_match_uses_newest_and_keeps_uid(self):
        cal, stats = merge.combine([('One', None, feed(summary='old')), ('Two', None, feed(modified='20261009T000000Z', summary='new'))], NOW)
        events = cal.walk('VEVENT')
        self.assertEqual(len(events), 1)
        self.assertEqual(str(events[0]['SUMMARY']), 'new')
        self.assertEqual(str(events[0]['UID']), 'match-1@gainline.app')
        self.assertEqual(stats['duplicates_removed'], 1)

    def test_club_labels_and_history(self):
        cal, stats = merge.combine([('Quins', 'Harlequins', feed(summary='Quins vs Sale')), ('Canes', 'Hurricanes', feed(uid='match-2', start='20250101T000000Z'))], NOW)
        self.assertEqual(str(cal.walk('VEVENT')[0]['SUMMARY']), 'Harlequins: Quins vs Sale')
        self.assertEqual(stats['old_events_removed'], 1)

    def test_gainline_floating_metadata_is_emitted_in_utc(self):
        body = feed(modified='20261001T000000')
        cal, _ = merge.combine([('Gainline', None, body)], NOW)
        output = cal.to_ical()
        self.assertIn(b'DTSTAMP:20261001T000000Z', output)
        self.assertIn(b'LAST-MODIFIED:20261001T000000Z', output)

    def test_cancellation_is_preserved(self):
        body = feed().replace(b'END:VEVENT', b'STATUS:CANCELLED\r\nEND:VEVENT')
        cal, _ = merge.combine([('Cancelled', None, body)], NOW)
        self.assertEqual(str(cal.walk('VEVENT')[0]['STATUS']), 'CANCELLED')

    def test_malformed_source_does_not_replace_published_calendar(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'rugby.ics'
            out.write_text('previous good feed')
            with patch.object(merge, 'fetch', return_value=('Broken', None, b'<html>error</html>')):
                with self.assertRaises(ValueError):
                    merge.refresh(out, NOW)
            self.assertEqual(out.read_text(), 'previous good feed')

    def test_empty_calendar_is_valid(self):
        empty = b'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\nEND:VCALENDAR\r\n'
        cal, _ = merge.combine([('Off season', None, empty)], NOW)
        self.assertEqual(cal.walk('VEVENT'), [])

    def test_reject_html_or_missing_uid(self):
        for body in [b'<html>outage</html>', feed().replace(b'UID:match-1@gainline.app\r\n', b'')]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                merge.combine([('Bad', None, body)], NOW)

    def test_failed_refresh_does_not_replace_published_calendar(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'rugby.ics'
            out.write_text('previous good feed')
            with patch.object(merge, 'fetch', side_effect=RuntimeError('upstream unavailable')):
                with self.assertRaises(RuntimeError):
                    merge.refresh(out, NOW)
            self.assertEqual(out.read_text(), 'previous good feed')
            self.assertFalse((out.parent / 'status.json').exists())

if __name__ == '__main__':
    unittest.main()
