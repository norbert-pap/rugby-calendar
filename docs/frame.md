# Combined rugby calendar

## Frame
Requirement: one auto-updating Proton subscription combining Harlequins, Hurricanes (NZ), and Gainline's men's senior international competitions.
Mode: HOLD. Reuse the verified Gainline feeds; no application, account integration, or private Proton data.
Approach: scheduled GitHub Action builds a public ICS file every six hours. Proton subscribes to its raw GitHub URL. Deduplicate on Gainline match UID; newest modification wins. Keep the preceding 30 days and future fixtures. On any source failure, leave the published calendar unchanged.
Escalation: operator must approve a new public `norbert-pap/rugby-calendar` repository before publication.
Out of scope: women's, development A/XV, club leagues other than the two selected teams, private events, and hosting costs.

## Spike
Live Gainline feeds exist for both clubs and all eight selected international competitions. Some international competitions currently return valid empty calendars. Team feeds include extensive historical results, so trim old fixtures before publication. No shared UIDs were found among the currently populated international competition feeds.

## Decision
The operator asked for all selected rugby calendars together. Public hosting approval is pending; local preparation is authorized. Separate sources remain available until Proton successfully syncs the combined feed.
