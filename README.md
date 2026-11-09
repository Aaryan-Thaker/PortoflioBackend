# Portfolio Platform Backend

A secure, high-performance Python/Flask backend serving the Next.js 15 portfolio platform frontend ([turiya_portfolio_platform](https://github.com/turiya-portfolio-platform)). 

Built for serverless execution on **Vercel** with a **PostgreSQL** database, this service provides portfolio tracking, automated FIFO lot accounting, XIRR annualized performance calculations, risk assessment profiling, and external market data lookups with in-memory TTL caching.

---

## Features

- **Google OAuth Authentication**: Token verification via `google-auth` validating bearer tokens forwarded by the Next.js API proxy (`/api/proxy/*`), with UUID-mapped user records in PostgreSQL.
- **FIFO Accounting & Valuation Engine**: Accurate First-In, First-Out (FIFO) cost basis calculation for Buy and Sell lots, real-time portfolio market valuation, realized and unrealized capital gains breakdowns, and Newton-Raphson XIRR return calculations.
- **TTL In-Memory Market Data Cache**: External quotes and index lookups (`yfinance`) are cached in memory using `cachetools.TTLCache` (5-minute TTL, 256-item ticker cache & 32-item index cache) with graceful fallbacks to protect against third-party rate limits.
- **Dynamic & Hardened CORS**: Safe CORS resolution configured dynamically from `ALLOWED_ORIGINS`, supporting credentialed requests (`Access-Control-Allow-Credentials: true`) without insecure wildcard origins.
- **Risk Profiling Engine**: Multi-factor questionnaire evaluation determining investor risk tolerance brackets (Defensive, Moderate, Aggressive, Very Aggressive).
- **Automated CI/CD**: Fully tested test suite with `pytest` running on GitHub Actions across Python 3.11 environments.

---

## Project Structure

```text
PortoflioBackend/
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
└── vercel.json                  # Vercel serverless function routing configuration
```

---

## Environment Variables

Copy `.env.example` to `.env` for local development:

```bash
cp .env.example .env
```

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `FLASK_ENV` | Application environment (`development`, `production`, `testing`) | `development` |
| `FLASK_SECRET_KEY` | Secret key for session security (**mandatory in production**) | `dev_secret_key_change_in_production` |
| `DATABASE_URL` | PostgreSQL connection string with host and database name | `postgresql://postgres:postgres@localhost:5432/portfolio_db` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID for verifying ID tokens | `your_google_client_id.apps.googleusercontent.com` |
| `ALLOWED_ORIGINS` | Comma-separated origins allowed to make CORS requests | `http://localhost:3000,https://turiya-portfolio-platform.vercel.app` |
| `PORT` | Local server port | `5000` |

> [!IMPORTANT]
> When `FLASK_ENV=production`, the application strictly requires `FLASK_SECRET_KEY` to be configured. If it is omitted or empty, `create_app()` will raise a `ValueError` to prevent deploying with insecure default secrets.

---

## API Reference

All protected endpoints require an `Authorization: Bearer <google_id_token>` header.

### System & Authentication

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/ping` | No | Base health check endpoint (returns `{"ping": "pong"}`). |
| `POST` | `/api/oauth/login` | Yes | Verifies Google ID token, registers or retrieves user, and returns profile. |

### Portfolio & Valuation

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/portfolio` | Yes | Returns overall valuation, sector allocations, holdings, and cached indices. |
| `GET` | `/api/portfolio/valuation` | Yes | Returns detailed valuation metrics, invested cost, and gains. |
| `GET` | `/api/stock/validate` | Yes | Validates ticker symbol (e.g. `?ticker=AAPL`) using TTL-cached market data. |

### Transactions Management

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/transactions` | Yes | Retrieves authenticated user's transactions enriched with live stock info. |
| `POST` | `/api/transactions` | Yes | Adds a single transaction (`type`, `stock`, `quantity`, `price`, `date`, `notes`). |
| `POST` | `/api/transactions/bulk` | Yes | Bulk uploads transactions via JSON array or raw CSV payload. |
| `GET` | `/api/transactions/summary`| Yes | Returns total invested, total value, realized/unrealized gains, and XIRR. |
| `POST` | `/api/transactions/clear` | Yes | Deletes all transactions for the authenticated user. |

### Risk Assessment

| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/risk/questionnaire` | No | Retrieves questions and weighting options for the risk assessment. |
| `POST` | `/api/risk/submit` | Yes | Submits questionnaire answers, stores profile, and computes risk bracket. |
| `GET` | `/api/risk/profile` | Yes | Retrieves the latest computed risk profile for the user. |

---

## Local Setup & Development

### 1. Prerequisites
- Python 3.11+
- PostgreSQL database (or Supabase / Neon PostgreSQL instance)
- Git

### 2. Clone and Setup Environment

```bash
git clone https://github.com/aaryanthaker/PortoflioBackend.git
cd PortoflioBackend

# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r api/requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your PostgreSQL credentials and Google Client ID
```

### 5. Run the Application

```bash
python api/index.py
```

The server will start at `http://localhost:5000`. You can verify it with:

```bash
curl http://localhost:5000/api/ping
```

---

## Running Tests

The test suite uses `pytest` and mocks external dependencies (PostgreSQL, Google OAuth token verification, and Yahoo Finance) to ensure fast, deterministic runs:

```bash
# Run all unit tests
pytest -v

# Run with coverage report
pytest --cov=api tests/
```

---

## Deployment (Vercel)

The repository is configured for zero-config serverless deployment via [`vercel.json`](file:///c:/Users/Aarya/projects/PortoflioBackend/vercel.json):

1. Link the repository to your Vercel project:
   ```bash
   vercel
   ```
2. Configure environment variables in the Vercel Dashboard under **Project Settings > Environment Variables**:
   - `FLASK_ENV`: `production`
   - `FLASK_SECRET_KEY`: *(Generate a secure random 32+ character string)*
   - `DATABASE_URL`: `postgresql://user:password@host:5432/dbname?sslmode=require`
   - `GOOGLE_CLIENT_ID`: `your_client_id.apps.googleusercontent.com`
   - `ALLOWED_ORIGINS`: `https://turiya-portfolio-platform.vercel.app,http://localhost:3000`

3. Deploy to production:
   ```bash
   vercel --prod
   ```
