# Implementation plan
- **Mode:** HOLD (from `docs/sports-calendars-frame.md`)
1. Add regression tests for exact cycling allowlist, women's exclusion, stage titles, darts majors/session selection, malformed/empty sources, next-year availability and failure-safe publication. Run red first.
2. Add sports.py using existing merge primitives. Fetch current cycling year and optionally next year (404 only means not published); validate all eight race families before history pruning. Explicit darts major allowlist, preserve published timestamps and source UIDs. Separate status files.
3. Add independent scheduled workflow matrix for the two new sports, sharing rugby's concurrency group to prevent publication races. Document stable subscription URLs and source/coverage limits.
4. Run whole unittest suite, live refresh both sports, reparse artifacts and inspect included events. Independent review, fix concrete defects, then commit and open PR. Publish authorized subscriptions and verify scheduled workflows and raw URLs.
Engineering review: no new service/dependency, reuse existing merger; current source failure leaves last-good files, only explicit next-year 404 is optional. Empty or drifted feeds must fail rather than silently publish nothing. Tests cover filtering, UTC/all-day preservation, recovery and year rollover. No rendered interface. Generated files are publication outputs, not extra architectural components.

Review fixes: explicitly check out the current branch tip for each sequential matrix job, because default checkout otherwise pins both to the trigger SHA and the second push fails. Added native Windows commands. Codex review completed; Claude exited before producing a review.
