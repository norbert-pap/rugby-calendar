# Implementation plan
Mode: HOLD (from docs/frame.md).
1. Test UID deduplication, newest-record selection, club labels, history trimming, malformed source rejection, legitimate empty feeds, and preservation of the previous file on failure.
2. Build a parser-based merger with an explicit ten-source allowlist; publish only after all fetches validate. Log source counts and record last successful refresh in status.json.
3. Add scheduled/manual GitHub workflow; test and build before committing.
4. Independent engineering review: parser and failure handling, narrow public data scope, workflow permissions, and Proton interoperability.
5. After public repository approval, commit and push, run the workflow, and verify the public ICS response and counts.
6. Add the combined Proton subscription, verify initial sync, then hide old rugby calendars to prevent duplicate display. Keep the old feeds recoverable.
7. Save UI proof and delivery details.

Engineering assessment: raw GitHub hosting needs no new credentials or server; repo-local workflow token is sufficient. Failure is fail-closed and never replaces a working feed with partial data. GitHub schedule timing and Proton's refresh polling are not exact. Long source outages or absent fixtures remain upstream limitations.
