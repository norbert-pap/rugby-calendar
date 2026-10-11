# Separate sports subscriptions
<!-- FRAME:BEGIN -->
Mode: HOLD. Extend the existing repository and publishing pattern; keep rugby unchanged.
Requirement: two independent auto-updating public ICS feeds: men's Grand Tours and five Monuments; major televised PDC darts tournaments and published sessions.
Approach: filter upstream subscriptions with explicit allowlists; reuse merge.combine for stable UIDs, validation, deduplication, history pruning and UTC metadata. Independent jobs prevent one sport's outage blocking another. No calendar-account access needed.
Out of scope: all UCI races, women's cycling, routine PDC floor/European Tour events, WDF, guessed broadcast times.
<!-- FRAME:END -->
<!-- SPIKE:BEGIN -->
Live source probe on 2026-10-11: Calendario Ciclismo's 2026-wt and 2027-wt feeds parsed successfully, providing all eight requested race families. 2026 contains stage timings, 2027 mostly all-day race spans. CSWStats parsed 32 events, including tournament spans and sessions, through the January 2027 World Championship final. Source availability does not establish exhaustive coverage; dates/times depend on upstream publishers.
<!-- SPIKE:END -->
<!-- DECIDE:BEGIN -->
Keep direction: user's request authorizes separate published subscriptions following rugby's existing setup. Use major PDC events including World Cup, Premier League and World Series Finals; exclude individual exhibition Masters. Calendario titles are translated to familiar English race names. Men's scope applies to cycling; PDC open majors may include women qualifiers.
<!-- DECIDE:END -->
