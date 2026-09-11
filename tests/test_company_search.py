"""Tests for company-name search (core/resolver.py + GET /api/v1/search)."""
import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from api.routes import router, validate_query
from core.resolver import (
    is_free_tier_supported,
    rank_candidates,
    resolve_best,
    search_companies,
    _is_valid_cached_search,
    _normalize_alpha_vantage,
    _normalize_finnhub,
    _search_finnhub,
)

import core.resolver

# Resolver runs on mock data in tests (see conftest.py)
core.resolver._TEST_MODE_OVERRIDE = True


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


CANDIDATES = [
    {"symbol": "APLE", "name": "Apple Hospitality REIT Inc", "type": "Common Stock", "region": "United States"},
    {"symbol": "AAPL", "name": "Apple Inc", "type": "Common Stock", "region": "United States"},
]


class TestRanking:
    def test_exact_symbol_ranks_first(self):
        ranked = rank_candidates(CANDIDATES, "AAPL")
        assert ranked[0]["symbol"] == "AAPL"

    def test_exact_name_ranks_first(self):
        ranked = rank_candidates(CANDIDATES, "apple inc")
        assert ranked[0]["symbol"] == "AAPL"

    def test_substring_match(self):
        ranked = rank_candidates(CANDIDATES, "hospitality")
        assert ranked[0]["symbol"] == "APLE"

    def test_dedupes_symbols(self):
        dupes = CANDIDATES + [dict(CANDIDATES[0])]
        ranked = rank_candidates(dupes, "apple")
        symbols = [c["symbol"] for c in ranked]
        assert len(symbols) == len(set(symbols))

    def test_drops_empty_symbols(self):
        ranked = rank_candidates([{"symbol": "", "name": "No Symbol", "type": "", "region": ""}], "no")
        assert ranked == []

    def test_empty_input(self):
        assert rank_candidates([], "apple") == []


class TestResolveBest:
    def test_single_candidate_auto_resolves(self):
        best, ambiguous = resolve_best("tesla", [CANDIDATES[1]])
        assert best["symbol"] == CANDIDATES[1]["symbol"]
        assert ambiguous == []

    def test_exact_match_auto_resolves(self):
        best, ambiguous = resolve_best("AAPL", CANDIDATES)
        assert best["symbol"] == "AAPL"
        assert ambiguous == []

    def test_partial_match_is_ambiguous(self):
        best, ambiguous = resolve_best("APPLE", CANDIDATES)
        assert best is None
        assert {c["symbol"] for c in ambiguous} == {"AAPL", "APLE"}
        # Best-ranked first
        assert ambiguous[0]["symbol"] == "AAPL"

    def test_no_candidates(self):
        assert resolve_best("zzznope", []) == (None, [])


class TestNormalize:
    def test_normalize_finnhub(self):
        payload = {"count": 1, "result": [
            {"description": "Apple Inc", "displaySymbol": "AAPL", "symbol": "AAPL", "type": "Common Stock"},
            {"description": "", "displaySymbol": "", "symbol": "", "type": ""},
        ]}
        out = _normalize_finnhub(payload)
        assert out == [{"symbol": "AAPL", "name": "Apple Inc", "type": "Common Stock", "region": ""}]

    def test_normalize_alpha_vantage(self):
        payload = {"bestMatches": [
            {"1. symbol": "AAPL", "2. name": "Apple Inc", "3. type": "Equity", "4. region": "United States"},
        ]}
        out = _normalize_alpha_vantage(payload)
        assert out[0]["symbol"] == "AAPL"
        assert out[0]["region"] == "United States"

    def test_normalize_alpha_vantage_malformed(self):
        assert _normalize_alpha_vantage({}) == []
        assert _normalize_alpha_vantage({"bestMatches": None}) == []


class TestSearchCompanies:
    def test_mock_search_apple(self):
        ranked = asyncio.run(search_companies("apple"))
        assert ranked[0]["symbol"] == "AAPL"
        assert all({"symbol", "name", "type", "region"} <= set(c) for c in ranked)

    def test_mock_search_no_match(self):
        assert asyncio.run(search_companies("zzznope123")) == []

    def test_short_query_rejected(self):
        assert asyncio.run(search_companies("a")) == []

    def test_finnhub_skipped_without_key(self, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(settings, "FINNHUB_API_KEY", "")
        assert asyncio.run(_search_finnhub("apple")) == []


class TestFreeTier:
    def test_us_tickers_supported(self):
        assert is_free_tier_supported("AAPL") is True
        assert is_free_tier_supported("MSFT") is True
        assert is_free_tier_supported("BRK.B") is True  # US class share
        assert is_free_tier_supported("MKC.V") is True  # US class share, not TSX-V
        assert is_free_tier_supported("AAPL", "United States") is True

    def test_international_suffixes_blocked(self):
        for sym in ["164A.T", "LMT.MX", "RELIANCE.NS", "BP.L",
                    "MC.PA", "SAP.DE", "0700.HK", "RY.TO",
                    "LMT.NE", "ABC.CN", "PINEAPP.KL", "ABC.J"]:
            assert is_free_tier_supported(sym) is False, sym

    def test_explicit_region_wins(self):
        assert is_free_tier_supported("XYZ", "India") is False
        assert is_free_tier_supported("XYZ", "United States") is True
        # Unknown region/suffix defaults to supported (never lock out)
        assert is_free_tier_supported("XYZ", "") is True
        assert is_free_tier_supported("XYZ.QQ") is True

    def test_ranked_candidates_carry_flag(self):
        ranked = rank_candidates(
            [{"symbol": "RELIANCE.NS", "name": "Reliance", "type": "Equity", "region": "India"}],
            "reliance",
        )
        assert ranked[0]["freeTierSupported"] is False


class TestCacheValidation:
    def test_old_shape_rejected(self):
        old = {"candidates": [
            {"symbol": "164A.T", "name": "Applepark", "type": "Common Stock", "region": ""}
        ]}
        assert _is_valid_cached_search(old) is False

    def test_new_shape_accepted(self):
        new = {"candidates": [
            {"symbol": "164A.T", "name": "Applepark", "type": "Common Stock",
             "region": "", "freeTierSupported": False}
        ]}
        assert _is_valid_cached_search(new) is True

    def test_empty_list_accepted(self):
        assert _is_valid_cached_search({"candidates": []}) is True

    def test_garbage_rejected(self):
        assert _is_valid_cached_search(None) is False
        assert _is_valid_cached_search({}) is False
        assert _is_valid_cached_search({"candidates": "nope"}) is False
        assert _is_valid_cached_search({"candidates": [{"symbol": "X"}]}) is False

    def test_stale_cache_self_heals(self, monkeypatch):
        """An old-shape cached payload is ignored and overwritten, not served."""
        import os
        import core.resolver
        from core.cache import get_cached_response, set_cached_response, _get_cache_path

        # Bypass mock mode so the real cache path is exercised
        monkeypatch.setattr(core.resolver, "_is_test_mode", lambda: False)
        monkeypatch.setenv("USE_MOCK_DATA", "false")
        monkeypatch.setattr(core.resolver, "_search_finnhub",
                            AsyncMock(return_value=[]))
        monkeypatch.setattr(core.resolver, "_search_alpha_vantage",
                            AsyncMock(return_value=[]))

        stale = {"candidates": [
            {"symbol": "164A.T", "name": "Applepark", "type": "", "region": ""}
        ]}
        set_cached_response("SEARCH:TESTSTALE", "SEARCH", stale)
        cache_file = _get_cache_path("SEARCH:TESTSTALE", "SEARCH")
        try:
            assert asyncio.run(search_companies("teststale")) == []
            # Cache overwritten with valid (empty) new-shape payload
            assert get_cached_response("SEARCH:TESTSTALE", "SEARCH") == {"candidates": []}
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)


class TestValidateQuery:
    def test_valid_names(self):
        assert validate_query("Apple") == "Apple"
        assert validate_query("  Johnson & Johnson  ") == "Johnson & Johnson"
        assert validate_query("L'Oreal") == "L'Oreal"

    def test_too_short(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            validate_query("a")
        assert exc.value.status_code == 400

    def test_bad_characters(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_query("Apple!!!")
        with pytest.raises(HTTPException):
            validate_query("rm -rf /")


class TestSearchEndpoint:
    def test_search_apple(self, client):
        resp = client.get("/api/v1/search/apple")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) and len(data) > 0
        assert data[0]["symbol"] == "AAPL"
        assert all({"symbol", "name", "type", "region"} <= set(c) for c in data)

    def test_search_no_match_returns_empty_list(self, client):
        resp = client.get("/api/v1/search/zzznope123")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_flags_free_tier_support(self, client):
        resp = client.get("/api/v1/search/reliance")
        assert resp.status_code == 200
        data = resp.json()
        intl = next(c for c in data if c["symbol"] == "RELIANCE.NS")
        assert intl["freeTierSupported"] is False

        resp = client.get("/api/v1/search/apple")
        us = next(c for c in resp.json() if c["symbol"] == "AAPL")
        assert us["freeTierSupported"] is True

    def test_search_too_short(self, client):
        assert client.get("/api/v1/search/a").status_code == 400

    def test_search_bad_characters(self, client):
        assert client.get("/api/v1/search/%21%21%21").status_code == 400


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
