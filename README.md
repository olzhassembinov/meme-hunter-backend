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