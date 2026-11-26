# Status — Backend

Last updated: 2026-11-26
Deployed: **yes**, production `https://api.zyangame.online` runs `dev` at `e6a547b` (deployed 2026-11-26) as the systemd service `memehunter`

## Implemented and working

- Player registration and profile: `POST /players`, `GET /players/{id}` (coins, XP, rank, XP booster, daily streak)
- Progression: XP for every catch (coins × 5), ranks derived from XP, XP booster bought with coins (×2 / ×5 for 24 h)
- `GET /leaderboard` (top by XP plus the player's own position) and `GET /players/{id}/collection`
- Daily streak counted on photo submissions (Almaty days); streak freeze bought with coins (40 coins, max 2 held)
- Card hunting: `GET /cards/nearby` (approximate positions), `POST /cards/{id}/claim` (reveals the exact position, reserves the card for 30 minutes, `expires_at` in the response)
- Spots and respawn: a caught card comes back at its spot after 1 hour, rarity weighted towards spots with few photos; background job every minute; admin `POST/GET /admin/spots`
- Photo submission: `POST /submissions` with one JPEG; coins credited instantly; the response always returns `status: "sent"`
- Zones (PostGIS): `play_area` (cards only inside it, currently the KBTU campus) and `restricted`/`dangerous` (no cards inside); enforced in nearby, claim and admin card creation
- Admin API (`X-Admin-Key`): create/list/deactivate zones, create cards
- Staff web pages (`/staff`): login (admin/reviewer roles), review queue, review screen with photo, map, distance and 6-group accessibility form, accept/reject with reason
- Doskaz handoff: automatic sending switched off; admins send selected accepted submissions with a button
- Database migrations with Alembic (revisions 0001–0007)
- HTTPS through nginx; the app listens on 127.0.0.1 only
- The app runs as a systemd service and the database container restarts automatically; both come back after a server reboot (checked 2026-11-26)
- Beta data on the server: KBTU campus play area and 3 spots (ramp, wheelchair parking sign, tactile tiles) with 7 card slots each

## In progress

- Nothing on a branch. Next, after the beta build: admin map page in the staff "Game" section (draw zones, place
  spots and cards on a map) and the meme library (admin adds, edits and removes memes; pictures served by the backend)

## Known gaps / not implemented yet

- `level` is legacy and always 1; use `rank`
- Rank names are placeholders (`rank_1` … `rank_5`)
- **Cards have no fixed meme picture**: no meme library yet; the client chooses the picture by rarity
- **No player authentication**: anyone who knows a `player_id` can act as that player
- Only the light priority rule exists (photo count per spot); the full priority formula and hunting areas are not implemented
- Spots must be created through the admin API (no map page yet)
- **`/cards/nearby` has no radius**: it returns every active card in the play area
- **One photo per submission** (multi-photo planned)
- Coins can only be spent on the XP booster and streak freezes (no shop)
- No zones map page for admins (zones are drawn on geojson.io and sent with Postman)
- No stats page; no automatic doskaz review-status feedback
- Doskaz token is copied by hand and expires
- Postgres port 5432 is reachable from the internet (to be closed)
- iOS: backend-side nothing blocks it (HTTPS meets App Transport Security)

## Recent changes

1. `e6a547b` Progression, spawning and streak merged into `dev` and deployed; app runs as a systemd service
2. `2f13ba8` Daily streak and streak freeze
3. `f0ae866` Spots, 30-minute claim timeout and card respawn
4. `b5ad768` XP, ranks, XP booster, leaderboard and collection
5. `8d2c98d` README rewritten as API/ops reference; STATUS.md added
