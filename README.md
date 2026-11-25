# Meme Hunter — Backend

Backend of **Meme Hunter**, a location-based mobile game (Unity, Android/iOS) that turns the collection of
accessibility data about city infrastructure into a game. Players walk to real places, "catch" meme cards there
and photograph the place (ramps, entrances, tactile paving, parking signs). Staff review the photos, and accepted
data can be handed over to [doskaz.kz](https://doskaz.kz) ("Доступный Казахстан"), the national accessibility map.

This README is the reference for anyone working against the backend: the Unity client, designers, and their tools.
**What is implemented right now, and what is not, is in [STATUS.md](STATUS.md).** The history of how the backend
was built phase by phase is in [docs/phase-guide.md](docs/phase-guide.md).

---

## At a glance

| | |
|---|---|
| Stack | Python 3.13, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 17 + PostGIS 3.6, Jinja2 (staff pages) |
| Production URL | `https://api.zyangame.online` |
| Hosting | Kamatera VPS (Ubuntu): nginx with HTTPS → uvicorn on `127.0.0.1:8000`; Postgres in Docker |
| Player auth | None yet: the client sends its `player_id` with each request |
| Admin auth | `X-Admin-Key` header (API) and username/password login (staff web pages) |

## How data flows

```
Player app ──► GET /cards/nearby ──► POST /cards/{id}/claim ──► POST /submissions (photo)
                                                                     │  coins credited instantly
                                                                     ▼
                                              Staff review page (/staff): accept / reject,
                                              fill in 6 accessibility groups
                                                                     │  admin presses "Send to doskaz"
                                                                     ▼
                                                               doskaz.kz request
```

- Players never see review results or anything about doskaz. The reward is paid at submission time.
- Cards exist only inside an active **play area** (currently the KBTU campus) and never inside a
  **restricted** or **dangerous** zone (roads, construction, etc.).

---

## Game API (used by the Unity client)

Base URL: `https://api.zyangame.online` (local development: `http://localhost:8000`).
Interactive docs: `/docs` (Swagger UI).

Conventions:
- IDs are UUID strings.
- Errors have the shape `{"detail": "<message>"}`.
- Coordinates are WGS84 decimal degrees (`lat`, `lng`).

### `GET /health`
Liveness check. → `200 {"status": "ok"}`

### `POST /players`
Create a player (registration = choosing a name).

Request (JSON):
```json
{ "display_name": "Olly" }
```
Response `200`:
```json
{ "id": "8c05163d-…", "display_name": "Olly", "currency_balance": 0, "level": 1 }
```
The client stores `id` and sends it with every later request.

### `GET /players/{player_id}`
Current player data (use it to refresh the coin balance).
Response `200`: same shape as above. `404 {"detail": "Player not found"}`.

> `level` exists but is not used yet (always `1`).

### `GET /cards/nearby?lat=<float>&lng=<float>`
Cards a player can hunt.

Response `200`:
```json
[
  { "id": "ae8bbba4-…", "rarity": "rare", "approx_lat": 43.256, "approx_lng": 76.943 }
]
```
- Returns **all** active cards inside the play area. `lat`/`lng` are accepted but not used for filtering yet (no radius).
- Positions are rounded to 3 decimals (~100 m). The exact position is revealed only by `claim`.
- `rarity` is one of `common`, `rare`, `epic`, `legendary`.

### `POST /cards/{card_id}/claim`
Start hunting a card. It becomes reserved for this player.

Request (form-data): `player_id`

Response `200`:
```json
{ "card_id": "ae8bbba4-…", "lat": 43.2552918, "lng": 76.9436849, "rarity": "rare" }
```
- `400 {"detail": "Card not available to claim"}`: the card is already claimed or caught, inactive, or outside the play area.
- Cards are **shared**: once claimed, nobody else can take it.

### `POST /submissions`
Send the photo of a claimed card.

Request (multipart form-data):

| Field | Type | Notes |
|---|---|---|
| `player_id` | text | must be the player who claimed the card |
| `card_id` | text | |
| `lat`, `lng` | text (float) | where the player stood |
| `photo` | file | one JPEG, max 10 MB (nginx limit) |

Response `200`:
```json
{ "submission_id": "6ce1a298-…", "status": "sent", "reward": 20 }
```
- `status` is always `"sent"` once the photo is stored and the coins are credited. The client must not interpret it further.
- `reward` = the card's coins; they are added to `currency_balance` immediately.
- `400 {"detail": "Card must be claimed by this player first"}`.
- The card becomes `submitted` and disappears from the map.

### Card rarity and rewards (beta data)

| Rarity | Coins |
|---|---|
| common | 10 |
| rare | 20 |
| epic | 40 |
| legendary | 80 |

The reward is stored per card (`base_reward`), so other values are possible. Cards have **no fixed meme picture**
yet; the client chooses a picture by rarity.

---

## Admin API (`X-Admin-Key` header)

For setup tasks from Postman. The key is `ADMIN_API_KEY` in `.env`.

| Method & path | Body | What it does |
|---|---|---|
| `POST /admin/zones` | `{"name", "kind", "geojson"}` | Create zone(s). `kind`: `play_area`, `restricted` or `dangerous`. `geojson`: a Polygon/MultiPolygon, Feature or FeatureCollection (output of geojson.io works as is). Returns created zones and `cards_deactivated` |
| `GET /admin/zones` | – | Active zones with geometry (`?include_inactive=true` for all) |
| `POST /admin/zones/{id}/deactivate` | – | Turn a zone off (deactivated cards are not restored) |
| `POST /admin/cards` | `{"lat", "lng", "rarity"?, "base_reward"?, "bonus_reward"?}` | Create a card. `409` if inside a blocked zone or outside the play area |
| `GET /admin/submissions` | – | Raw list of submissions (legacy, prefer the staff pages) |
| `POST /admin/submissions/{id}/review?decision=` | – | Legacy review endpoint (prefer the staff pages) |

Zone rules:
- **play_area:** if at least one is active, cards may exist only inside one. With none, the whole map is open.
- **restricted / dangerous:** no cards inside, even within the play area.
- Creating a zone deactivates existing cards that break the rules.
- The rules use `cards.location`, which Postgres computes from `lat`/`lng`, so cards inserted with plain SQL follow them too.

## Staff web pages (`/staff`)

Browser UI for reviewers and admins: `https://api.zyangame.online/staff`.

| Page | Who | Purpose |
|---|---|---|
| `/staff/login` | all staff | username + password (accounts are created with `scripts/create_staff.py`) |
| `/staff/queue` | all staff | Pending / Accepted / Rejected tabs, photo thumbnails, distance player↔card (red if > 50 m) |
| `/staff/submissions/{id}` | all staff | Large photo, map with card and player positions, accessibility form (6 groups: movement, limb, vision, hearing, intellectual, kids; full/partial/no/unknown), Accept / Reject with reason. Keyboard: A accept, R reject, N skip |
| "Send to doskaz" form | admin only | On accepted submissions: object name, address, category → sends the photo and a summary to doskaz |

Roles: `admin` and `reviewer` (stored in the `staff` table, separate from players).
Photos are only served to logged-in staff.

## Doskaz handoff

- Automatic sending on submission is **off** (`DOSKAZ_HANDOFF_ENABLED=false`); submissions are stored with `handoff_status = held`.
- An admin sends selected accepted submissions from the review page (`held`/`failed` → `sent`/`failed`).
- Doskaz auth is a manually copied `ACCESS_TOKEN` cookie value (`DOSKAZ_ACCESS_TOKEN`). It expires and must be refreshed by hand.

---

## Data model (main tables)

| Table | Key columns |
|---|---|
| `players` | `id`, `display_name`, `currency_balance`, `level`, `created_at` |
| `cards` | `id`, `lat`, `lng`, `location` (PostGIS point, computed), `rarity`, `base_reward`, `bonus_reward`, `status` (`active`/`claimed`/`submitted`/`inactive`), `claimed_by_player_id`, `claimed_at` |
| `submissions` | `id`, `player_id`, `card_id`, `lat`, `lng`, `photo_path`, `handoff_status` (`held`/`sent`/`failed`), `review_status` (`pending`/`accepted`/`rejected`), `reviewer_id`, `reviewed_at`, `reject_reason`, `accessibility` (JSON), `created_at` |
| `zones` | `id`, `name`, `kind`, `area` (PostGIS geometry), `is_active`, `created_at` |
| `staff` | `id`, `username`, `password_hash` (bcrypt), `role`, `is_active` |
| `pending_bonuses` | legacy, no longer written |

All timestamps are stored as UTC. Staff pages show Almaty time.
The schema is managed with **Alembic** (`alembic/versions/`). Never create or change tables by hand.

---

## Running locally

Requirements: Python 3.13+, PostgreSQL with PostGIS (Postgres.app or Homebrew, or `docker compose up -d`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create .env with the variables below
alembic upgrade head        # creates / updates all tables
python -m scripts.create_staff <username> admin
uvicorn app.main:app --reload
```

`.env` variables:

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | e.g. `postgresql+asyncpg://localhost/memehunter` |
| `DOSKAZ_BASE_URL` | default `https://doskaz.kz` |
| `DOSKAZ_ACCESS_TOKEN` | doskaz `ACCESS_TOKEN` cookie value |
| `ADMIN_API_KEY` | key for the `X-Admin-Key` header |
| `SESSION_SECRET` | random string that signs the staff login cookie (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `SESSION_HTTPS_ONLY` | `true` on the server (HTTPS), `false` locally |
| `DOSKAZ_HANDOFF_ENABLED` | `false` (default): no automatic sending to doskaz |

`.env.db` (only for `compose.yml`): `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

Schema changes: edit `app/models.py`, then
```bash
alembic revision --autogenerate -m "what changed"   # review the generated file
alembic upgrade head
```

## Deploying to the server

On the server, in `/root/backend` (the server follows the `dev` branch):

```bash
git pull
uv pip install -r requirements.txt
uv run alembic upgrade head
pkill -f "uvicorn app.main:app"
nohup uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 > nohup.out 2>&1 &
curl -s localhost:8000/health
```

The app is not a system service yet: after a server reboot it must be started again with the `nohup` line.
Back up the database before migrations:
`docker exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > ~/backup-$(date +%F).sql`

## Repository layout

```
app/
  main.py            app setup, routers, staff session cookie
  config.py          settings from .env
  database.py        async engine and sessions
  models.py          SQLAlchemy models (tables)
  schemas.py         request/response models for players
  routers/           game API (players, cards, submissions) and admin API (admin, admin_zones), doskaz debug route
  staff/             staff web pages: login, review queue, review screen, doskaz sending
  templates/staff/   HTML templates for the staff pages
  static/            CSS for the staff pages
  zones.py           zone rules (play area, blocked zones)
  handoff.py         sending a submission to doskaz
  doskaz_client.py   HTTP client for doskaz.kz
  timeutil.py        UTC storage / Almaty display helpers
alembic/             database migrations
scripts/             create_staff.py
docs/                phase-guide.md (build history)
STATUS.md            current state of the backend
```
