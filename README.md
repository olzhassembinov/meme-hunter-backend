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