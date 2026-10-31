# Plan: Sports calendar viewing channels
- **Goal:** Add viewing labels to existing sports events automatically from current provider listings, leaving uncertain events unlabelled.
- **Mode:** SELECTIVE EXPANSION (from `brainstorm-notes/2026-10-31-watch-channels.md`).
- **Architecture:** Optional watch.py enrichment runs after calendar construction and before atomic publication in merge.py and sports.py; GitHub Actions supplies one encrypted credential bundle. Provider failure skips labels without preventing fixture refresh.
- **Tech stack:** Python, icalendar, urllib; `python -m unittest -v`.
- **Global constraints:** Same UIDs, starts, ends, summaries and subscription URLs; strict existing sport allowlists; no credentials, stream URLs or full catalogue in public outputs/logs; no guessing channel or broadcast rights; preserve original descriptions. Only list channels that the UHF sports filter admits.

## Files
- `watch.py` — optional bounded provider queries, conservative matching, source broadcaster hints, event-description enrichment.
- `test_watch.py` — matcher, privacy, cancellation, dates, repeated runs and outage regression checks.
- `merge.py`, `sports.py` — call enrichment once at publication and add safe counts to status.
- `.github/workflows/refresh.yml`, `.github/workflows/sports.yml` — encrypted secret input, triggers and branch-tip checkout.
- `README.md` — behaviour, setup and limits.

### Task 1 — Match listings and enrich descriptions
**Interfaces:** `enrich(calendar, now) -> dict` mutates only descriptions and emits safe counts; configured via WATCH_PROVIDER_JSON (url,username,password). Tests use explicit records and mocked HTTP, never live credentials.
**Steps:** Write failing tests: actual Exeter Chiefs/Harlequins fixture matched to STAN12 listing on adjacent date; wrong opponent/date/women/cancelled rejected; unrelated original description retained; repeat invocation replaces own block; optional missing credentials and provider HTTP failures produce no secret-bearing output. Implement conservative matching and bounded reads, then wire both publishers after construction. Preserve source-supplied generic broadcaster as a broadcaster hint, never a guessed exact channel.
<!-- AC:BEGIN -->
- [ ] #1 Exeter fixture receives STAN12 label plus “UHF: search Exeter”.
- [ ] #2 UIDs, SUMMARY, DTSTART, DTEND and pre-existing description remain unchanged except appended owned viewing block.
- [ ] #3 Tests reject wrong opponent, wrong date, cancelled fixture and women's listing for men's fixture.
- [ ] #4 Missing/failed provider never prevents fixture publication or prints credentials.
<!-- AC:END -->

### Task 2 — Activate scheduled integration
**Steps:** Add encrypted secret bundle to workflow environment and watch code/test push triggers; branch-tip checkout in rugby refresh. Add documentation; set repository secret from existing Pi credentials without printing it. Run local enrichment on current fixtures, count matches, inspect safe example.
<!-- AC:BEGIN -->
- [ ] #1 Both existing publishers invoke enrichment exactly once before serialisation.
- [ ] #2 Only safe labels/hints reach calendar files and logs; no stream URLs or credentials are published.
- [ ] #3 Existing test suite passes; full current calendar parses and retains fixture counts/identities/times.
<!-- AC:END -->

### Task 3 — Verify + PR
**Steps:** Fresh reviewer checks diff, fix findings, run full suite, commit and open PR with evidence. User has authorised activation: merge only after checks/review succeed, run existing publication jobs and verify raw published ICS includes an event viewing block. Proton remains a polling subscriber; do not claim its UI refreshed without inspection.
<!-- AC:BEGIN -->
- [ ] #1 Review has no unresolved material findings.
- [ ] #2 Tests pass and PR contains validation evidence.
- [ ] #3 Published feed retains subscription URL and contains the new viewing information where matched.
<!-- AC:END -->

Plan review: seven implementation files reuse existing publisher, no new persistent service, no router dependency. Main failure modes are stale slots, ambiguous names, source outages and leaked URL exceptions; conservative date/name matching, no guesses, optional enrichment and sanitised exception handling address these. No plan contradictions found.
