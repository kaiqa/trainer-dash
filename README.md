# Training Planner Dashboard

A modern, production-ready dashboard for managing training sessions received via webhook from Dogbrah AI Fitness Coach. Built with FastAPI, MySQL, and vanilla JavaScript.

The dashboard transforms the old meeting request system into a fitness training planner that records, tracks, and manages workout sessions. Each session includes detailed training metrics, body part tracking, injury monitoring, pain reporting, and a user-provided rating.

## Features

- 🔄 **Real-time Updates** - WebSocket-powered live dashboard updates when new training sessions arrive
- 📊 **Modern Dashboard** - Clean, responsive UI with statistics (planned, done, skipped, total), advanced filtering, sorting, and pagination
- ⚡ **Status Tracking** - Each session has a status: `planned`, `done`, or `skipped` - click the status badge to cycle through states
- ⚙️ **Configurable Webhook** - Settings page to configure listen IP, port, and path
- 📥 **Export Data** - Download training sessions as JSON or CSV (bulk or single session)
- 🗄️ **MySQL Backend** - Reliable data persistence with proper indexing
- 🐳 **Docker Ready** - Production-ready Docker Compose deployment
- 🧪 **Comprehensive Tests** - Pytest suite with webhook, API, settings, and WebSocket tests (115 tests passing)
- 🌙 **Dark/Light Theme** - Automatic theme detection with manual toggle support
- 💪 **Fitness Metrics** - Track sets, repetitions, weight, body type, injuries, pain, and ratings
- 📈 **Analytics Page** - Bar charts (body type, training type) and doughnut charts (status, rating distribution) via Chart.js

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Dogbrah AI    │────▶│  Webhook Endpoint │────▶│   MySQL     │
│ (Fitness Coach) │     │ /webhook/record-training       │
└─────────────────┘     └────────┬─────────┘     └─────────────┘
                              │
                  ┌────────────┴────────────┐
                  ▼                         ▼
          ┌───────────────┐         ┌───────────────┐
          │  WebSocket    │         │  REST API     │
          │  Broadcast    │         │  /api/trainings│
          └───────┬───────┘         └───────┬───────┘
                  ▼                         ▼
          ┌───────────────┐         ┌───────────────┐
          │  Dashboard    │         │  Dashboard    │
          │  (Real-time)  │         │  (CRUD/Export)│
          └───────────────┘         └───────────────┘
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and navigate
cd trainer-dash

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, change MYSQL_ROOT_PASSWORD and DB_PASSWORD

# Start services (Docker Compose V2)
docker compose up -d

# View logs
docker compose logs -f app
```

The dashboard will be available at `http://localhost:5687` and the training webhook at `http://localhost:5687/webhook/record-training`.

### Initialize Default Settings

On first run, initialize default webhook settings via API:
```bash
curl -X POST http://localhost:5687/api/settings/initialize-defaults
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Set up environment
cp .env.example .env
# Edit .env for local development (use SQLite for simplicity)

# Run database migrations (tables created automatically on startup)
# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 5687
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `production` | Application environment |
| `APP_HOST` | `0.0.0.0` | Host to bind the server |
| `APP_PORT` | `5687` | Port to bind the server |
| `DEBUG` | `false` | Enable debug mode |
| `DB_HOST` | `mysql` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `meetings_user` | MySQL username |
| `DB_PASSWORD` | `meetings_password` | MySQL password |
| `DB_NAME` | `meetings_db` | MySQL database name |
| `DATABASE_URL` | - | Full database URL (overrides individual settings) |
| `WEBHOOK_HOST` | `0.0.0.0` | Webhook listen IP (configurable via UI) |
| `WEBHOOK_PORT` | `5687` | Webhook listen port (configurable via UI) |
| `WEBHOOK_PATH` | `/webhook/req-meeting` | Webhook endpoint path |
| `CORS_ORIGINS` | `["http://localhost:5687"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Webhook Configuration

The webhook endpoint can be configured via the **Settings** page in the dashboard:

- **Listen IP**: IP address to bind (e.g., `0.0.0.0` for all interfaces, `100.66.60.70` for specific interface)
- **Port**: Port number (default: `5687`)
- **Path**: Endpoint path (default: `/webhook/record-training`)

**Example configurations:**
- `http://100.66.60.70:5687/webhook/record-training`
- `http://localhost:5687/webhook/record-training`

> **Note**: Changes to webhook settings may require application restart to take effect.

## Verified Endpoints

All endpoints tested and verified working:

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/health` | GET | ✅ | Application health check |
| `/webhook/health` | GET | ✅ | Webhook health check |
| `/webhook/record-training` | POST | ✅ | Receive training session (Dogbrah AI) |
| `/api/trainings` | GET | ✅ | List trainings (paginated, filterable) |
| `/api/trainings/{id}` | GET | ✅ | Get single training session |
| `/api/trainings/{id}` | PATCH | ✅ | Update training session |
| `/api/trainings/{id}/status` | PATCH | ✅ | Update only status (planned/done/skipped) |
| `/api/trainings/{id}` | DELETE | ✅ | Delete training session |
| `/api/trainings/export/all` | GET | ✅ | Export all as JSON |
| `/api/trainings/export/csv` | GET | ✅ | Export all as CSV |
| `/api/trainings/stats/summary` | GET | ✅ | Get statistics summary |
| `/api/settings` | GET | ✅ | Get all settings |
| `/api/settings/{key}` | GET | ✅ | Get setting by key |
| `/api/settings/{key}` | PUT | ✅ | Create/update setting |
| `/api/settings/webhook-url` | GET | ✅ | Get full webhook URL |
| `/api/settings/training-webhook-url` | GET | ✅ | Get full training webhook URL |
| `/api/settings/initialize-defaults` | POST | ✅ | Initialize default settings |
| `/ws` | WS | ✅ | WebSocket for real-time updates |

## API Documentation

### Webhook Endpoint

#### Receive Training Session
```
POST /webhook/record-training
Content-Type: application/json
```

The webhook accepts training session data from Dogbrah AI Fitness Coach:

```json
{
  "user_name": "kai",
  "time_spend_minutes": 30,
  "date": "29.09.2026",
  "time": "10:00",
  "type": "squats",
  "sets": "3",
  "repetitions": "12",
  "weight": "77",
  "body_type": "legs",
  "injuries": "no",
  "pain": "yes",
  "pain_source": "knees",
  "rating": "7",
  "session_notes": "it was a hard training and my knees did hurt a little but nothing major give a rating 7 out of ten stars"
}
```

**Required fields:**
- `user_name`: Full name of the user
- `time_spend_minutes`: Time spent in minutes
- `date`: Training date in `DD.MM.YYYY` format (e.g., `29.09.2026`)
- `time`: Training time in `HH:MM` format (e.g., `10:00`)
- `type`: Training type (e.g., `squats`, `bench_press`, `deadlift`)
- `sets`: Number of sets
- `repetitions`: Number of repetitions per set
- `body_type`: Body type trained (`legs`, `chest`, `back`, `shoulders`, `arms`, `core`)
- `injuries`: Whether user has injuries (`yes` or `no`)
- `pain`: Whether user experienced pain (`yes` or `no`)

**Optional fields:**
- `weight`: Weight in kg
- `pain_source`: Source of pain (required when `pain` is `yes`)
- `rating`: Training rating from 1 to 10
- `session_notes`: Session notes

**Status:**
Each new session is created with `status: planned`. You can update it via the API:
- `planned` - Session planned or in progress
- `done` - Session completed
- `skipped` - Session skipped

**Response:** `201 Created` with training session object

### REST API Endpoints

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | `/api/trainings` | List trainings (paginated, filterable) |
| GET | `/api/trainings/{id}` | Get single training session |
| PATCH | `/api/trainings/{id}` | Update training session |
| PATCH | `/api/trainings/{id}/status` | Update only status (planned/done/skipped) |
| DELETE | `/api/trainings/{id}` | Delete training session |
| GET | `/api/trainings/export/all` | Export all trainings as JSON |
| GET | `/api/trainings/export/csv` | Export all trainings as CSV |
| GET | `/api/trainings/stats/summary` | Get statistics summary |

### Query Parameters for `/api/trainings`

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20, max: 100) |
| `search` | string | Search in user name, type, body type |
| `user_name` | string | Filter by exact user name |
| `status` | string | Filter by status: `planned`, `done`, `skipped` |
| `body_type` | string | Filter by body type |
| `date_from` | date | Filter from date (inclusive, format: YYYY-MM-DD) |
| `date_to` | date | Filter to date (inclusive, format: YYYY-MM-DD) |
| `sort` | string | Sort field:direction — added: `sets`, `repetitions`, `time_spent_minutes`, `weight`, `training_time` |

### WebSocket Endpoint

```
WS /ws
```

**Message Types:**
- `training_created` - New training session received
- `training_updated` - Training session status or details changed
- `training_deleted` - Training session removed

**Example message:**
```json
{
  "type": "training_created",
  "data": {
    "id": 1,
    "user_name": "kai",
    "time_spent_minutes": 30,
    "training_date": "2026-09-29",
    "training_time": "10:00:00",
    "type": "squats",
    "sets": 3,
    "repetitions": 12,
    "weight": 77.0,
    "body_type": "legs",
    "injuries": "no",
    "pain": "yes",
    "pain_source": "knees",
    "rating": 7,
    "session_notes": "it was a hard training...",
    "status": "planned",
    "created_at": "2026-09-29T10:00:00",
    "updated_at": "2026-09-29T10:00:00"
  }
}
```

## Dashboard Usage

### Dashboard Page
- **Statistics Cards** - Total Sessions, Planned, Done, Skipped counts
- **Search** - Filter by user name, training type, or body type
- **Advanced Filters** - User Name (exact match), Status (`planned`/`done`/`skipped`), Body Type, Date Range (From/To), Sort options, Page size
- **Clear Filters** - One-click button to reset all filters
- **Table** - Sortable columns including Date, Rating, Status; sticky header; inline actions per row
- **Actions per row:**
  - 👁 View Details - Editable session info (name, sets, reps, weight, rating, notes, status, etc.) with Save Changes button
  - ↻ Update Status - Change between planned/done/skipped (modal dropdown)
  - 🏷 **Click Status Badge** - Click any status badge to instantly cycle: Planned → Done → Skipped → Planned
  - ⬇ Download - Export single session as JSON
  - 🗑 Delete - Permanent removal (with confirmation)
- **Bulk Export** - Download all as JSON or CSV
- **Pagination** - Navigate through pages

### Status Workflow
The training planner supports a simple but powerful status workflow:
1. When Dogbrah AI sends a session, it's created with `status: planned`
2. After completing the workout, update to `status: done`
3. If the session is missed, update to `status: skipped`
4. You can also update details (sets, repetitions, rating, notes) anytime

**Quick Status Toggle:** Click any status badge in the table to instantly cycle:
`Planned` → `Done` → `Skipped` → `Planned`

### Settings Page
- Configure webhook listen IP, port, and training webhook path
- Live preview of full webhook URL for Dogbrah AI
- Copy URL to clipboard
- Reset to defaults
- Application info display

## Testing

### Run All Tests
```bash
# Using pytest directly
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# In Docker test environment
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

### Test Structure
```
tests/
├── conftest.py          # Fixtures and configuration
├── __init__.py
├── test_webhook.py      # Webhook endpoint tests (legacy + new)
├── test_trainings.py    # Training API endpoint tests
├── test_settings.py     # Settings API endpoint tests
└── test_websocket.py    # WebSocket tests
```

### Test Markers
```bash
# Run only webhook tests
pytest tests/ -m webhook -v

# Run only training endpoint tests
pytest tests/ -m training -v

# Run only API tests
pytest tests/ -m api -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

## Fake Data Generator

Generate realistic fake training sessions using Faker with full webhook compatibility:

```bash
# Generate 10 fake sessions (default) to file
python generate_fake_training_sessions.py

# Generate 50 sessions
python generate_fake_training_sessions.py 50

# Send directly to webhook endpoint
python generate_fake_training_sessions.py 5 --host localhost --port 5687 --send-to-webhook

# Custom output file
python generate_fake_training_sessions.py 20 -o /tmp/my_trainings.json

# JSON Lines format
python generate_fake_training_sessions.py 10 --format jsonl
```

The script uses `faker` to generate realistic names, random dates (last 90 days), training types (`squats`, `bench_press`, etc.), body types, injuries/pain (with dependency), ratings, and session notes. All fields match the webhook payload format (`DD.MM.YYYY` dates, string numeric values for sets/reps/weight/rating).

## Database Schema

### `trainings` Table
```sql
CREATE TABLE trainings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,
    time_spent_minutes INT NOT NULL,
    training_date DATE NOT NULL,
    training_time TIME NOT NULL,
    type VARCHAR(100) NOT NULL,
    sets INT NOT NULL,
    repetitions INT NOT NULL,
    weight INT NULL,
    body_type VARCHAR(100) NOT NULL,
    injuries VARCHAR(10) NOT NULL DEFAULT 'no',
    pain VARCHAR(10) NOT NULL DEFAULT 'no',
    pain_source VARCHAR(255) NULL,
    rating INT NULL,
    session_notes TEXT NULL,
    status ENUM('planned', 'done', 'skipped') DEFAULT 'planned' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    INDEX ix_trainings_user_name (user_name),
    INDEX ix_trainings_training_date (training_date),
    INDEX ix_trainings_type (type),
    INDEX ix_trainings_body_type (body_type),
    INDEX ix_trainings_status (status),
    INDEX ix_trainings_status_created (status, created_at),
    INDEX ix_trainings_user_date (user_name, training_date),
    INDEX ix_trainings_body_type_date (body_type, training_date)
);
```

### `settings` Table
```sql
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) UNIQUE NOT NULL,
    `value` TEXT NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## Project Structure

```
trainer-dash/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection & sessions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── meeting.py       # Legacy meeting model (retained)
│   │   ├── training.py      # Training session SQLAlchemy model
│   │   └── setting.py       # Settings SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── meeting.py       # Legacy meeting schemas (retained)
│   │   ├── training.py      # Pydantic schemas for trainings
│   │   └── setting.py       # Pydantic schemas for settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── webhook.py       # Legacy meeting webhook (retained)
│   │   ├── training_webhook.py  # Training webhook endpoint
│   │   ├── trainings.py     # Training REST API
│   │   ├── meetings.py      # Legacy meetings REST API (retained)
│   │   └── settings.py      # Settings REST API
│   ├── services/
│   │   ├── __init__.py
│   │   └── websocket.py     # WebSocket manager
│   └── static/
│       ├── index.html       # Training dashboard HTML
│       ├── style.css        # Modern CSS with CSS variables
│       └── app.js           # Vanilla JS dashboard logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures (includes training fixtures)
│   ├── test_webhook.py      # Webhook endpoint tests
│   ├── test_trainings.py    # Training API endpoint tests
│   ├── test_settings.py     # Settings API endpoint tests
│   └── test_websocket.py    # WebSocket tests
├── Dockerfile               # Multi-stage production build
├── Dockerfile.test          # Test environment
├── docker-compose.yml       # Production deployment
├── docker-compose.test.yml  # Test deployment
├── generate_fake_training_sessions.py  # Generate fake sessions (count param + webhook send)
├── init-db.sql              # Database initialization (includes trainings table)
├── requirements.txt         # Production dependencies
├── requirements-test.txt    # Test dependencies
├── pytest.ini               # Pytest configuration
├── .env.example            # Environment template
├── .env.test.example       # Test environment template
└── README.md                # This file
```

## Troubleshooting

### Common Issues

**Webhook not receiving requests:**
- Verify Dogbrah AI is sending to the correct URL (`http://YOUR_IP:5687/webhook/record-training`)
- Check firewall allows port 5687
- Verify `WEBHOOK_HOST` is set to `0.0.0.0` (not `localhost` or `127.0.0.1`)
- Confirm `date` is in `DD.MM.YYYY` format and `time` is in `HH:MM` format
- If `pain` is `yes`, `pain_source` must be provided

**Status Updates:**
- Use `PATCH /api/trainings/{id}/status` with `{"status": "done"}` or `{"status": "skipped"}`
- The full `PATCH /api/trainings/{id}` endpoint can also update `status` along with other fields

**Database connection failed:**
- Ensure MySQL container is healthy: `docker-compose ps`
- Check credentials in `.env` match MySQL environment variables
- View logs: `docker-compose logs mysql`

**WebSocket not connecting:**
- Ensure reverse proxy supports WebSocket upgrades
- Check CORS origins include your domain
- Browser console for connection errors

**Settings not persisting:**
- Settings are stored in MySQL `settings` table
- Use Settings page or API to modify webhook configuration
- The `training_webhook_path` controls the training webhook endpoint

### Logs

```bash
# Application logs
docker compose logs -f app

# Database logs
docker compose logs -f mysql

# All logs
docker-compose logs -f
```

## Development

### Adding New Features

1. Create model in `app/models/`
2. Create schema in `app/schemas/`
3. Add API routes in `app/api/`
4. Update database (handled automatically on startup)
5. Add tests in `tests/`
6. Update frontend in `app/static/` if needed

### Code Style

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/
```

### Status Workflow Example

When the Dogbrah AI fitness coach records a session, it sends the data to `/webhook/record-training`. The webhook creates the session with `status: planned`. After the user completes the workout, they update the status via the dashboard or API:

```bash
# Mark session as done
curl -X PATCH http://localhost:5687/api/trainings/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"done"}'
```

If the session is skipped:

```bash
curl -X PATCH http://localhost:5687/api/trainings/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"skipped"}'
```

## License

MIT License - Feel free to use and modify for your needs.

## Support

For issues and feature requests, please open a GitHub issue.

Note: The `init-db.sql` script creates the `trainings` table with the status enum (`planned`, `done`, `skipped`). The old `meetings` table is retained for backward compatibility.
