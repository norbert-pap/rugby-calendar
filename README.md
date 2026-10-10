# Rugby calendar

One auto-updating calendar for Harlequins, Hurricanes (New Zealand), and men's senior international rugby union.

Subscribe in Proton Calendar using:

```
https://raw.githubusercontent.com/norbert-pap/rugby-calendar/main/rugby.ics
```

Only public Gainline fixtures are included. This repository contains no Proton account information or private events.

## Coverage

- Harlequins (men)
- Hurricanes (NZ)
- Men's Six Nations, Rugby Championship, international friendlies, World Cup, Nations Championship, Lions Series, Pacific Nations Cup, Rugby Europe Championship

Women's and A/XV development competitions are excluded. Lions coverage follows Gainline's series feed and can include tour matches against clubs. Coverage is only as complete as Gainline's published fixtures; empty feeds become populated when the source publishes a schedule.

## Refresh and operation

GitHub Actions refreshes at 00:17, 06:17, 12:17 and 18:17 UTC. Scheduled jobs can be delayed. Each successful refresh publishes `status.json` with source counts and last refresh time. Run **Actions → Refresh rugby calendar → Run workflow** for a manual refresh. GitHub Actions failures identify the failed source and retain the last published calendar. Regular refresh commits keep repository activity current; if scheduling stops, check Actions and manually enable/run the workflow.

Proton polls external subscriptions on its own schedule (typically every 4–16 hours), so changes may not appear immediately. Initial import can take several minutes. This feed is under Proton's 1 MB subscription limit.

Fixtures use their original stable Gainline UID and original UTC match times. Duplicate UIDs are collapsed, preferring the newest source update. Club fixtures receive a team prefix. Fixtures older than 30 days are removed. Source fetch or validation failure prevents partial publication.

## Local refresh

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
.venv/bin/python merge.py
```

Sources: https://gainline.app/ and https://beta.gainline.app/en/leagues
