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

## Cycling and darts — separate subscriptions

Subscribe by URL in Proton Calendar (do not import a one-off download):

- Cycling: https://raw.githubusercontent.com/norbert-pap/rugby-calendar/main/cycling.ics
- Darts: https://raw.githubusercontent.com/norbert-pap/rugby-calendar/main/darts.ics

**Cycling:** men's Giro d'Italia, Tour de France, Vuelta a España, Milan-San Remo, Tour of Flanders, Paris-Roubaix, Liège-Bastogne-Liège and Il Lombardia only. Current and next-year men's WorldTour feeds from [Calendario Ciclismo](https://calendariociclismo.app/en/subscription/) are filtered by exact race name and UCI category. Race/stage titles are translated to English. Grand Tours appear as individual stages when the source publishes them, otherwise as an all-day race span. No guessed start times or rest-day stages are added. Source end times can be estimates. The next year is retried every refresh if not yet published (HTTP 404); other failures retain the last-good feed. All eight race families must be present in each published source year before filtering old events.

**Darts:** World Championship, World Masters, Premier League, UK Open, World Cup, World Matchplay, World Grand Prix, European Championship, Grand Slam, Players Championship Finals, World Series Finals and European Open, when included by [CSWStats](https://cswdarts.co.uk/darts-calendar). Excludes routine Players Championships, European Tour, women's-only events and individual World Series exhibition Masters. PDC open majors may include women qualifiers. Includes all-day tournament spans and published timed sessions. UK TV channels in titles describe the source's UK coverage, not Hungarian rights. Session end times are upstream three-hour estimates; each calendar app displays the supplied UTC start in its own timezone. UK clock text is removed from session titles to avoid conflicting with your local time.

The new feeds refresh separately at 00:27, 06:27, 12:27 and 18:27 UTC, subject to GitHub scheduling delays. Each publishes its own `cycling-status.json` or `darts-status.json`; rugby's existing feed and workflow are unchanged. Failures retain that sport's previous publication and do not stop the other sport refreshing. Empty/malformed upstream feeds or an allowlist with no matches fail visibly. Future coverage depends on upstream publication: at setup on 11 October 2026, cycling includes all eight 2027 races, while darts reaches the World Championship ending 3 January 2027; later 2027 darts events are not yet in this source. Subscribe once to these stable URLs; cycling source years roll forward automatically.

Run manually via **Actions → Refresh cycling and darts calendars → Run workflow**. Locally:

```
.venv/bin/python -m unittest -v
.venv/bin/python sports.py cycling
.venv/bin/python sports.py darts
```

On Windows, use the virtual environment executable instead:

```powershell
.venv\Scripts\python.exe -m unittest -v
.venv\Scripts\python.exe sports.py cycling
.venv\Scripts\python.exe sports.py darts
```
