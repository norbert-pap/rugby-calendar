# Verification

- Local `python -m unittest -v`: 8 tests passed.
- Live merge: 10 sources validated, 69 unique events, 21,309 bytes; 396 old fixture records removed. Current output: 29 Harlequins fixtures and 40 international fixtures. Hurricanes source has 48 historical records, none within the retained window.
- Independent Codex reviewer found floating Gainline metadata timestamps; fixed DTSTAMP/LAST-MODIFIED/CREATED serialization to UTC and added regression tests. Re-review: no remaining blocking findings.
- Additional Claude CLI review could not connect: repeated ConnectionRefused to its configured endpoint. No review result is claimed from that attempt.
- Operator approved public hosting on 10 October 2026. Repository published at https://github.com/norbert-pap/rugby-calendar.
- Hosted GitHub workflow 38036819870 succeeded: tests, all ten source fetches, generation and publication. Public ICS URL returned 69 events.
- Proton initial sync completed. Combined calendar named Rugby is enabled; original Rugby and all ten separate team/international feeds are hidden. Existing calendars were preserved.
- UI verified combined New Zealand–Australia result and Harlequins–Sale fixture. Proof screenshot saved locally as /tmp/proton-combined-rugby.png.
