import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from api.finance.utils import (
    compute_holdings_from_transactions,
    calculate_portfolio_xirr,
    capital_gains_breakdown,
    get_stock_info,
    get_index_quote,
    stock_info_cache,
    index_quote_cache,
)
from api.finance.transactions.csv_upload import (
    validate_and_normalize_transaction,
    parse_csv_string,
)


# ==============================================================================
# 1. Valuation & Return Calculation Logic
# ==============================================================================

def test_compute_holdings_fifo():
    """Test FIFO calculation logic for Buy and Sell transactions."""
    mock_stock_data = {
        "AAPL": {
            "symbol": "AAPL",
            "price": 180.0,
            "previousClose": 175.0,
            "shortName": "Apple Inc.",
            "currency": "USD",
        }
    }

    # Buy 10 @ $100, Buy 10 @ $120, Sell 5 @ $150 (FIFO: sells from first lot @ $100)
    transactions = [
        {"stock": "AAPL", "type": "Buy", "quantity": 10, "price": 100.0, "date": "2025-01-01"},
        {"stock": "AAPL", "type": "Buy", "quantity": 10, "price": 120.0, "date": "2025-01-10"},
        {"stock": "AAPL", "type": "Sell", "quantity": 5, "price": 150.0, "date": "2025-01-15"},
    ]

    with patch("api.finance.utils.get_stock_info", side_effect=lambda t: mock_stock_data.get(t, {})):
        holdings = compute_holdings_from_transactions(transactions)

    assert "AAPL" in holdings
    aapl = holdings["AAPL"]
    # 20 bought - 5 sold = 15 remaining
    assert aapl["quantity"] == 15
    # Remaining: 5 shares @ $100 ($500) + 10 shares @ $120 ($1200) = $1700 total cost
    assert aapl["total_cost"] == pytest.approx(1700.0)
    assert aapl["avg_cost"] == pytest.approx(1700.0 / 15)
    # Unrealized gain: (15 * $180) - $1700 = $1000
    assert aapl["unrealized_gain"] == pytest.approx(1000.0)
    # Realized gain on 5 sold: 5 * ($150 - $100) = $250
    assert aapl["realized_gain"] == pytest.approx(250.0)
    assert aapl["currency"] == "USD"


def test_portfolio_xirr_calculation():
    """Test XIRR calculation with positive returns."""
    transactions = [
        {"stock": "MSFT", "type": "Buy", "quantity": 10, "price": 200.0, "date": "2024-01-01"},
    ]

    mock_info = {
        "symbol": "MSFT",
        "price": 250.0,
        "currency": "USD",
    }

    with patch("api.finance.utils.get_stock_info", return_value=mock_info):
        xirr = calculate_portfolio_xirr(transactions)
        # Investment grew from $2000 to $2500, XIRR should be positive float
        assert xirr is not None
        assert isinstance(xirr, float)
        assert xirr > 0.0


def test_capital_gains_breakdown():
    """Test realized vs unrealized capital gains calculation."""
    transactions = [
        {"stock": "GOOGL", "type": "Buy", "quantity": 10, "price": 100.0, "date": "2025-01-01"},
        {"stock": "GOOGL", "type": "Sell", "quantity": 4, "price": 125.0, "date": "2025-02-01"},
    ]

    mock_info = {"symbol": "GOOGL", "price": 130.0, "currency": "USD"}

    with patch("api.finance.utils.get_stock_info", return_value=mock_info):
        breakdown = capital_gains_breakdown(transactions)
        # Realized gain: 4 * (125 - 100) = 100.0
        assert breakdown["total_realized"] == pytest.approx(100.0)
        # Unrealized gain: 6 * (130 - 100) = 180.0
        assert breakdown["total_unrealized"] == pytest.approx(180.0)
        assert breakdown["total_realized"] + breakdown["total_unrealized"] == pytest.approx(280.0)


# ==============================================================================
# 2. Input Validation on Transaction Routes
# ==============================================================================

def test_add_transaction_empty_payload(authenticated_client):
    """POST /api/transactions with empty payload should return 400."""
    res = authenticated_client.post(
        "/api/transactions",
        headers={"Authorization": "Bearer valid-token"},
        json={},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False


def test_add_transaction_invalid_fields(authenticated_client):
    """POST /api/transactions with invalid fields should return 400."""
    # Invalid transaction type
    res_type = authenticated_client.post(
        "/api/transactions",
        headers={"Authorization": "Bearer valid-token"},
        json={"type": "Hold", "stock": "AAPL", "quantity": 10, "price": 150.0, "date": "2025-01-01"},
    )
    assert res_type.status_code == 400

    # Negative quantity
    res_qty = authenticated_client.post(
        "/api/transactions",
        headers={"Authorization": "Bearer valid-token"},
        json={"type": "Buy", "stock": "AAPL", "quantity": -5, "price": 150.0, "date": "2025-01-01"},
    )
    assert res_qty.status_code == 400

    # Future date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    res_date = authenticated_client.post(
        "/api/transactions",
        headers={"Authorization": "Bearer valid-token"},
        json={"type": "Buy", "stock": "AAPL", "quantity": 10, "price": 150.0, "date": future_date},
    )
    assert res_date.status_code == 400
    assert "future" in res_date.get_json()["error"].lower()


def test_bulk_transactions_validation(authenticated_client):
    """POST /api/transactions/bulk validates payload structure."""
    # Missing transactions key
    res_missing = authenticated_client.post(
        "/api/transactions/bulk",
        headers={"Authorization": "Bearer valid-token"},
        json={},
    )
    assert res_missing.status_code == 400
    assert "No transactions provided" in res_missing.get_json()["error"]

    # Transactions is not a list
    res_not_list = authenticated_client.post(
        "/api/transactions/bulk",
        headers={"Authorization": "Bearer valid-token"},
        json={"transactions": "invalid_string"},
    )
    assert res_not_list.status_code == 400
    assert "must be an array" in res_not_list.get_json()["error"]


def test_csv_upload_parsing_and_normalization():
    """Test CSV string parsing and row validation."""
    valid_csv = "date,stock,type,quantity,price,notes\n2025-01-01,AAPL,Buy,10,150.50,Initial buy"
    rows = parse_csv_string(valid_csv)
    assert len(rows) == 1
    assert rows[0]["stock"] == "AAPL"

    normalized, errors = validate_and_normalize_transaction(rows[0])
    assert len(errors) == 0
    assert normalized["stock"] == "AAPL"
    assert normalized["type"] == "Buy"
    assert normalized["quantity"] == 10
    assert float(normalized["price"]) == 150.50

    # Invalid row test
    invalid_row = {"date": "invalid-date", "stock": "", "type": "Invalid", "quantity": -1, "price": -5}
    _, errors = validate_and_normalize_transaction(invalid_row)
    assert len(errors) > 0


# ==============================================================================
# 3. External Market Data TTL Caching & Graceful Fallbacks
# ==============================================================================

def test_stock_info_cache_hits_and_ttl():
    """Verify TTLCache avoids redundant external network calls for identical tickers."""
    assert stock_info_cache.maxsize == 256
    assert stock_info_cache.ttl == 300

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.info = {
            "symbol": "NVDA",
            "regularMarketPrice": 120.0,
            "previousClose": 118.0,
            "shortName": "NVIDIA Corporation",
            "currency": "USD",
        }
        mock_ticker_cls.return_value = mock_instance

        # First call: hits external source
        info1 = get_stock_info("NVDA")
        assert info1["price"] == 120.0
        assert mock_ticker_cls.call_count == 1

        # Second call (same symbol): should hit TTLCache directly
        info2 = get_stock_info("NVDA")
        assert info2["price"] == 120.0
        assert mock_ticker_cls.call_count == 1  # Not called again!

        # Case insensitive / whitespace normalization hits same cache
        info3 = get_stock_info("  nvda  ")
        assert info3["price"] == 120.0
        assert mock_ticker_cls.call_count == 1


def test_stock_info_graceful_failure():
    """Verify external lookup failures do not raise exceptions and return safe defaults."""
    with patch("yfinance.Ticker", side_effect=Exception("API connection timeout")):
        result = get_stock_info("FAILED_TICKER")
        assert result is not None
        assert result["symbol"] == "FAILED_TICKER"
        assert result["price"] is None
        assert result["currency"] == "USD"


def test_index_quote_cache_and_fallback():
    """Verify get_index_quote caches properly and handles API exceptions gracefully."""
    assert index_quote_cache.maxsize == 32
    assert index_quote_cache.ttl == 300

    # Successful call cached
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.info = {
            "regularMarketPrice": 5000.0,
            "previousClose": 4950.0,
        }
        mock_ticker_cls.return_value = mock_instance

        res1 = get_index_quote("^GSPC")
        assert res1["price"] == 5000.0
        assert mock_ticker_cls.call_count == 1

        # Second call hits cache
        res2 = get_index_quote("^GSPC")
        assert res2["price"] == 5000.0
        assert mock_ticker_cls.call_count == 1

    # Graceful fallback on exception
    with patch("yfinance.Ticker", side_effect=RuntimeError("Rate limit exceeded")):
        res_fail = get_index_quote("^DJI_FAIL")
        assert res_fail["price"] is None
        assert res_fail["change"] == 0.0
        assert res_fail["change_pct"] == 0.0
