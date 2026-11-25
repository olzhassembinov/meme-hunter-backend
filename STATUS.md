# Status — Backend

Last updated: 2026-11-25
Deployed: **yes**, production `https://api.zyangame.online` runs `dev` at `c194003` (deployed 2026-11-18)

## Implemented and working

- Player registration and profile: `POST /players`, `GET /players/{id}` (name, coin balance)
- Card hunting: `GET /cards/nearby` (approximate positions), `POST /cards/{id}/claim` (reveals the exact position, reserves the card)
- Photo submission: `POST /submissions` with one JPEG; coins credited instantly; the response always returns `status: "sent"`
- Zones (PostGIS): `play_area` (cards only inside it, currently the KBTU campus) and `restricted`/`dangerous` (no cards inside); enforced in nearby, claim and admin card creation
- Admin API (`X-Admin-Key`): create/list/deactivate zones, create cards
- Staff web pages (`/staff`): login (admin/reviewer roles), review queue, review screen with photo, map, distance and 6-group accessibility form, accept/reject with reason
- Doskaz handoff: automatic sending switched off; admins send selected accepted submissions with a button
- Database migrations with Alembic (revisions 0001–0004)
- HTTPS through nginx; the app listens on 127.0.0.1 only
- Beta data on the server: KBTU campus play area and 21 cards around 3 spots (ramp, wheelchair parking sign, tactile tiles)

## In progress

- README and STATUS documentation (this file)
- Next in this build: leaderboard, card collection, XP and ranks, XP booster bought with coins

## Known gaps / not implemented yet

- **No leaderboard and no collection endpoint** (being added now)
- **No XP, ranks or boosters**; `level` exists in the player data but is always 1
- **Cards have no fixed meme picture**: there are no card types; the client chooses the picture by rarity
- **No player authentication**: anyone who knows a `player_id` can act as that player
- **No claim timeout**: an abandoned claim keeps the card blocked until staff release it manually
- **No card respawn and no spawn/priority algorithm**: cards are placed by an admin; a caught card does not come back
- **`/cards/nearby` has no radius**: it returns every active card in the play area
- **One photo per submission** (multi-photo planned)
- No shop or other way to spend coins yet (the XP booster will be the first)
- No zones map page for admins (zones are drawn on geojson.io and sent with Postman)
- No stats page; no automatic doskaz review-status feedback
- Doskaz token is copied by hand and expires
- The app runs with `nohup`, not as a system service: it does not restart by itself after a server reboot
- Postgres port 5432 is reachable from the internet (to be closed)
- iOS: backend-side nothing blocks it (HTTPS meets App Transport Security)

## Recent changes

1. `c194003` Zone kind `play_area`: cards exist only inside the beta area
2. `ded3935` PostGIS safety zones; nearby, claim and card creation respect them
3. `10df5bd` Admin "Send to doskaz" button; staff pages show Almaty time
4. `1615ac1` Staff review queue and review screen
5. `f867a16` Staff accounts and login; Alembic migrations introduced shortly before (`d6a3c5e`)
