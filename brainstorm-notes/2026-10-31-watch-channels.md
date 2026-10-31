<!-- FRAME:BEGIN -->
- **Requirement:** Add verified viewing channels and UHF search hints to existing sports calendar event descriptions; preserve subscription URLs, fixture identities/times and existing sport scope.
- **Out of scope:** Playback links containing credentials, guessed broadcast rights, new calendar subscriptions, opening the Pi to the internet.
- **Mode:** SELECTIVE EXPANSION
- **Escalation line:** User supplies any missing administrator authentication; ambiguous event matches remain unlabelled.
<!-- FRAME:END -->

Premise: fixtures are already published by GitHub Actions; enrich those existing events instead of adding another calendar publisher. The useful outcome is knowing what to search for in UHF when a listed event has an identified feed. Existing merge.py/sports.py preserve original UIDs and use atomic publication.

Approaches: (1) enrich existing workflows using an optional provider catalogue loaded through encrypted repository secrets (chosen, no new network exposure); (2) add a public Pi endpoint (rejected, unnecessary exposure); (3) publish a manually copied slot map (rejected, STAN assignments change).

<!-- SPIKE:BEGIN -->
## Spike — 2026-10-31
**Made:** Read-only live provider query plus real calendar fixture read.
**Showed:** Provider currently lists AU STAN 12 Exeter v Harlequins, dated 2026-11-01 01:55:50; calendar has Exeter Chiefs vs Harlequins on 2026-10-31 15:00 UTC. Slot text uses a different clock and should not overwrite fixture time.
**What it changed:** Match both teams with explicit aliases and date tolerance; mark labels as provider listings, never proof of playback. Only source-supplied broadcaster labels can be used as broad hints.
<!-- SPIKE:END -->

<!-- DECIDE:BEGIN -->
## Decision — 2026-10-31
**keep.** User said “nice do it” after seeing event-description example.
**Escalated and answered:** No new subscription required. Channel names and UHF search instructions, without unverified deep links.
**Mode:** SELECTIVE EXPANSION.
<!-- DECIDE:END -->
