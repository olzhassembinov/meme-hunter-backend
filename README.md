# meme-hunter-backend
Backend of the game

What Phase 2 is: the backend learns what a "player" is. Everything later (claiming cards, submitting photos, getting rewards) has to be attached to a player, so this phase creates the players table and the two basic endpoints for it, create a player and fetch a player. There's no login yet, on purpose, because that comes after the core pipeline works.

What each file is for:

config.py reads .env into one settings object (database URL, doskaz token, admin key). Every other file imports settings from here instead of reading .env itself.
database.py creates the engine (the connection to Postgres) and get_db, which gives each incoming request its own database session and closes it when the request ends.
models.py has the Player class, which describes what the players table looks like: id, display_name, currency_balance, level, created_at. It's a blueprint in Python only, and Postgres knows nothing about it yet.
create_tables.py reads that blueprint and builds the real table in Postgres. You'll rerun it in later phases when new models are added.
schemas.py defines the shape of data going in and out of the API. PlayerCreate accepts only display_name from the client, and PlayerOut defines what the API returns. It's separate from the model so a client can never send its own currency_balance or level.
routers/players.py has the two endpoints, POST /players (create) and GET /players/{id} (fetch).
main.py gets one extra line that plugs the players router into the app.

## Phase 3: Backend ↔ doskaz connectivity

**What it is:** the first check that the backend can talk to doskaz.kz.
Everything later (uploading photos, submitting facility requests) goes
through the same client, so this phase proves the connection works before
any game logic depends on it.

**Files:**
- `app/doskaz_client.py`: `DoskazClient`, the single place that makes
  HTTP calls to doskaz. It reads the base URL and access token from the
  settings (`.env`) and sends the token in an `Authorization: Bearer`
  header. For now it has one method, `list_categories()`, which calls
  `GET /api/objects/categories` and returns doskaz's category list.
- `app/routers/doskaz.py`: a temporary debug endpoint,
  `GET /doskaz/categories`, that calls the client and returns the result.
  It exists so the connection can be tested from Postman without the rest
  of the pipeline. It can be removed once the real flow works.
- `app/main.py`: registers the doskaz router so the route exists.

**How to test:** start the server, send `GET /doskaz/categories` in
Postman. A list of categories means the backend reached doskaz. Note the
category `id` values, since Phase 6 needs one.

**Known limitations:**
- The categories endpoint is probably public, so a 200 proves the
  connection but not that the token is valid. The token is first truly
  tested in Phase 6.
- The doskaz website sends the token as an `ACCESS_TOKEN` cookie, while
  this client sends it as a Bearer header. If Phase 6 returns 401 with a
  fresh token, switch the client to send the cookie instead.
- The token is copied by hand from a logged-in browser session and
  expires, so it has to be refreshed periodically.


  ## Phase 4: Cards and claim

**What it is:** the client-facing side of the card hunt. The backend
can list the cards that are available, and a player can claim one. Claiming
is the point where the card's exact coordinates are handed to the client,
which uses them only for the local distance ("fog") effect and never shows
them to the player. Cards are seeded by hand for now. Real spawn logic
(priority zones from doskaz coverage) comes later.

**Files:**
- `app/models.py`: the `Card` model. It stores `lat`, `lng`, `rarity`,
  `base_reward` (paid instantly on submission, Phase 5) and `bonus_reward`
  (held as a pending bonus, Phase 5 and 7). `status` moves through
  `active` → `claimed` → `submitted`, and `claimed_by_player_id` and
  `claimed_at` record who claimed it and when.
- `app/routers/cards.py`:
  - `GET /cards/nearby`: returns every card with status `active`.
    `lat` and `lng` are accepted but not used to filter yet, so this
    proves the response shape the client will use.
  - `POST /cards/{card_id}/claim`: takes `player_id` as form data, locks
    the card to that player, and returns `lat`, `lng` and `rarity`.
    A card that isn't `active` returns 400.
- `app/main.py`: registers the cards router.

**How to test:**
1. Run `python create_tables.py` to create the `cards` table.
2. Insert test cards in DataGrip. Fill every column, because the defaults
   in `models.py` exist only in Python and plain SQL gets none of them.
3. `GET /cards/nearby?lat=43.238&lng=76.889` returns the active cards.
4. Create a player with `POST /players`, then `POST /cards/{id}/claim`
   with form-data `player_id`. It returns the coordinates, and the card
   becomes `claimed` in the database.
5. Claiming the same card again returns 400, and `nearby` no longer lists it.

**Known limitations:**
- `nearby` ignores the position and returns all active cards.
- Claiming doesn't check that the player exists. An unknown `player_id`
  fails on the foreign key and returns a 500.
- Two players claiming the same card at the same moment could both
  succeed, because the check and the update aren't locked.
- Timestamps are stored as naive UTC (`.replace(tzinfo=None)`), because
  the `claimed_at` column has no timezone and asyncpg rejects
  timezone-aware values.


## Phase 5 — Photo submission

`POST /submissions` (form-data: `player_id`, `card_id`, `lat`, `lng`, `photo`)

- The card must be `claimed` by the same player, otherwise the request is rejected with `400`. This is what makes the claim step mandatory.
- The photo is saved locally to `storage/photos/<uuid>.jpg` (gitignored).
- A `Submission` row is created and the card status becomes `submitted`.
- Two-stage reward:
  - the player gets the card's `base_reward` immediately;
  - a `PendingBonus` row is created for the card's `bonus_reward` with status `pending`. It is credited only after the admin API records an accepted review (Phase 7).
- The response contains only `submission_id`, `status` and the base `reward`. It reveals nothing about the pending bonus or the review.
- Submitting twice for the same card returns `400`, because the card is no longer `claimed`.

Tested in Postman and verified in DataGrip: `players.currency_balance` increases by exactly `base_reward`, and a matching `pending_bonuses` row exists.


## Phase 6 — doskaz handoff

After a submission is saved, the backend hands it to doskaz (`DoskazClient`):

1. `POST /api/storage/upload`: raw photo bytes, returns `{"path": "/storage/<hash>.jpeg"}`.
2. `POST /api/objects/requests`: a "small form" facility request referencing that path. Every accessibility attribute is sent as `not_provided`. doskaz answers `204 No Content`, so no object id comes back.

doskaz specifics (found by inspecting its own website in browser DevTools):
- Auth is the `ACCESS_TOKEN` **cookie** of one shared doskaz account (`DOSKAZ_ACCESS_TOKEN` in `.env`), not a Bearer header. The cookie lasts 31 days and must be refreshed by hand.
- CSRF is a double-submit pair: a random `XSRF-TOKEN` cookie plus an identical `X-Xsrf-Token` header, generated per client instance.
- `first.otherNames` must not be empty.

`submissions.handoff_status` becomes `sent` on success, or `failed` if doskaz rejects the request or is unreachable. The reason is printed to the server log. The player's reward is credited either way.