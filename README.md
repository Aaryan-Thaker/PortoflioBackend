```markdown
# Portfolio Platform Backend

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pytest](https://img.shields.io/badge/pytest-8.3.3-0A9EDC?style=flat-square&logo=pytest)](https://docs.pytest.org/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=github-actions)](https://github.com/Aaryan-Thaker/portfolio-backend/actions)

A secure, high-performance Python/Flask REST API serving the Next.js 15 portfolio platform frontend ([turiya_portfolio_platform](https://github.com/Aaryan-Thaker/turiya_portfolio_platform)).

This service handles portfolio valuation, automated FIFO (First-In, First-Out) lot accounting, annualized performance calculations (XIRR), risk assessment profiling, and external market data lookups backed by PostgreSQL and in-memory TTL caching.

---

## Features

- **Google OAuth Token Verification**: Decorator-based token verification via `google-auth` validating bearer tokens forwarded by the Next.js API proxy (`/api/proxy/*`), with UUID-mapped user records stored in PostgreSQL.
- **FIFO Accounting & Valuation Engine**: Accurate First-In, First-Out cost-basis tracking for Buy and Sell lots, real-time portfolio market valuation, realized and unrealized capital gains breakdowns, and Newton-Raphson XIRR return calculations.
- **TTL In-Memory Market Data Cache**: External quotes and index lookups (`yfinance`) are cached in memory using `cachetools.TTLCache` (5-minute TTL, 256-item ticker cache & 32-item index cache) with graceful fallbacks to protect against third-party rate limits.
- **Hardened CORS Policy**: Dynamic origin resolution configured strictly from `ALLOWED_ORIGINS`, supporting credentialed requests (`Access-Control-Allow-Credentials: true`) without insecure wildcard fallbacks.
- **Risk Profiling Engine**: Multi-factor questionnaire evaluation determining investor risk tolerance brackets (Defensive, Moderate, Aggressive, Very Aggressive).
- **Automated CI/CD**: Pytest suite integrated with GitHub Actions running continuous test verification across Python 3.11 environments.

---
```
## Project Structure

```text
portfolio-backend/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow (Python 3.11 + pytest)
├── api/
│   ├── auth/
│   │   ├── auth.py              # Google JWT verification decorator & client validation
│   │   ├── routes.py            # OAuth login and user record registration
│   │   └── __init__.py
│   ├── database/
│   │   ├── db.py                # PostgreSQL connection pooling & schema initialization
│   │   └── __init__.py
│   ├── finance/
│   │   ├── models.py            # Transaction database queries & normalization
│   │   ├── risk.py              # Investor risk questionnaire & scoring routes
│   │   ├── routes.py            # Portfolio, transaction, valuation & ticker endpoints
│   │   ├── utils.py             # FIFO logic, XIRR calculation & TTL quote caching
│   │   ├── __init__.py
│   │   └── transactions/
│   │       └── csv_upload.py    # CSV transaction string parser and validator
│   ├── index.py                 # Application factory (create_app), CORS & config
│   └── requirements.txt         # Pinned production & testing dependencies
├── tests/
│   ├── conftest.py              # Pytest fixtures and mock client configurations
│   ├── test_auth.py             # Auth, health check, CORS & secret key tests
│   └── test_portfolio.py        # FIFO accounting, valuation, validation & cache tests
├── .env.example                 # Template for required environment variables
├── .gitignore                   # Ignored files (secrets, caches, virtualenvs)
├── requirements.txt             # Root dependency reference (-r api/requirements.txt)
└── vercel.json                  # Serverless function rewrite rules

```

---

## Environment Variables

Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env

```

| Variable | Description | Example / Default |
| --- | --- | --- |
| `FLASK_ENV` | Application runtime environment (`development`, `production`, `testing`) | `development` |
| `FLASK_SECRET_KEY` | Cryptographic secret for session security (**mandatory in production**) | `dev_secret_key_change_in_production` |
| `DATABASE_URL` | PostgreSQL connection URI | `postgresql://postgres:postgres@localhost:5432/portfolio_db` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID for validating ID tokens | `your_google_client_id.apps.googleusercontent.com` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins | `http://localhost:3000` |
| `PORT` | Local runtime port | `5000` |

> **Security Note:** When `FLASK_ENV=production`, `FLASK_SECRET_KEY` must be set explicitly. If missing or left empty, `create_app()` raises a `ValueError` immediately at boot to prevent operating with insecure default keys.

---

## API Reference

All protected endpoints require an `Authorization: Bearer <google_id_token>` header.

### System & Authentication

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/ping` | No | Base health check endpoint (returns `{"ping": "pong"}`). |
| `POST` | `/api/oauth/login` | Yes | Verifies Google ID token, registers or retrieves user, and returns profile. |

### Portfolio & Valuation

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/portfolio` | Yes | Returns overall valuation, sector allocations, holdings, and cached indices. |
| `GET` | `/api/portfolio/valuation` | Yes | Returns valuation trajectory metrics, total invested cost, and gains. |
| `GET` | `/api/stock/validate` | Yes | Validates ticker symbol (e.g., `?ticker=AAPL`) using TTL-cached market data. |

### Transactions Management

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/transactions` | Yes | Retrieves authenticated user's transactions enriched with market data. |
| `POST` | `/api/transactions` | Yes | Records a single transaction (`type`, `stock`, `quantity`, `price`, `date`, `notes`). |
| `POST` | `/api/transactions/bulk` | Yes | Bulk uploads transactions via JSON array or CSV payload. |
| `GET` | `/api/transactions/summary` | Yes | Returns total invested, total value, realized/unrealized gains, and XIRR. |
| `POST` | `/api/transactions/clear` | Yes | Purges all transactions for the authenticated user. |

### Risk Assessment

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/risk/questionnaire` | No | Retrieves questions and weighting options for the risk assessment. |
| `POST` | `/api/risk/submit` | Yes | Submits questionnaire answers, stores profile, and computes risk bracket. |
| `GET` | `/api/risk/profile` | Yes | Retrieves the latest computed risk profile for the user. |

---

## Local Setup & Development

### 1. Prerequisites

* Python 3.11+
* PostgreSQL instance running locally or via cloud (Neon, Supabase)
* Git

### 2. Clone and Setup Environment

```bash
git clone git@github.com:Aaryan-Thaker/portfolio-backend.git
cd portfolio-backend

# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows (Git Bash):
source .venv/Scripts/activate

```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r api/requirements.txt

```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your local PostgreSQL credentials and Google Client ID

```

### 5. Start the Server

```bash
python api/index.py

```

The server will start at `http://localhost:5000`. Test connectivity with:

```bash
curl http://localhost:5000/api/ping

```

---

## Running Tests

The test suite uses `pytest` and mocks external dependencies (PostgreSQL queries, Google OAuth token verification, and Yahoo Finance network calls) for deterministic offline execution:

```bash
# Run all unit tests
pytest -v

# Run with coverage report
pytest --cov=api tests/

```

---

## Related Repositories

* **Frontend Web Application:** [Aaryan-Thaker/turiya_portfolio_platform](https://www.google.com/url?sa=E&source=gmail&q=https://github.com/Aaryan-Thaker/turiya_portfolio_platform) – Next.js 15 client dashboard featuring Plotly.js charts, AG Grid, and server-side NextAuth API proxying.

