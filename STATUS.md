# Status — Backend

Last updated: 2026-11-25
Deployed: **partly**, production `https://api.zyangame.online` runs `dev` at `c194003` (deployed 2026-11-18); progression (`feature/progression`) and spawning (`feature/spawning`) are not deployed yet

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

- Branch `feature/progression` (tested locally, not merged/deployed): XP for every catch (coins × 5), ranks derived from XP,
  XP booster bought with coins (×2 / ×5 for 24 h), `GET /leaderboard`, `GET /players/{id}/collection`, profile with
  `xp`, `rank`, `xp_to_next_rank`, `booster`; migration 0005 gives existing players the XP of their past catches
- Branch `feature/spawning` (tested locally, on top of progression): spots, 30-minute claim timeout (`expires_at` in the
  claim response), automatic respawn 1 hour after a catch, rarity of respawned cards weighted towards spots with few
  photos, admin `POST/GET /admin/spots`, background job every minute; migration 0006
- Next: deploy both branches (plus running the app as a system service), then the zones/spots map page for admins

## Known gaps / not implemented yet

- Leaderboard, collection, XP, ranks and booster are **not on the server yet** (branch `feature/progression`); `level` is legacy and always 1
- Rank names are placeholders (`rank_1` … `rank_5`)
- **Cards have no fixed meme picture**: there are no card types; the client chooses the picture by rarity
- **No player authentication**: anyone who knows a `player_id` can act as that player
- Claim timeout and respawn exist only on `feature/spawning` (not on the server yet); on the server an abandoned claim still blocks a card and caught cards do not come back
- Only the light priority rule exists (photo count per spot); the full priority formula and hunting areas are not implemented
- Spots must be created through the admin API (no map page yet)
- **`/cards/nearby` has no radius**: it returns every active card in the play area
- **One photo per submission** (multi-photo planned)
- The XP booster is the only way to spend coins (no shop)
- No zones map page for admins (zones are drawn on geojson.io and sent with Postman)
- No stats page; no automatic doskaz review-status feedback
- Doskaz token is copied by hand and expires
- The app runs with `nohup`, not as a system service: it does not restart by itself after a server reboot
- Postgres port 5432 is reachable from the internet (to be closed)
- iOS: backend-side nothing blocks it (HTTPS meets App Transport Security)

## Recent changes

1. `b5ad768` XP, ranks, XP booster, leaderboard and collection (branch `feature/progression`)
2. `8d2c98d` README rewritten as API/ops reference; STATUS.md added
3. `c194003` Zone kind `play_area`: cards exist only inside the beta area
4. `ded3935` PostGIS safety zones; nearby, claim and card creation respect them
5. `10df5bd` Admin "Send to doskaz" button; staff pages show Almaty time
