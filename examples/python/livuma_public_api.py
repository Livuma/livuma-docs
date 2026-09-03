"""Minimal client for Livuma's public, key-free API (https://livuma.com/api/public).

Standard library only. Python 3.9+.

    from livuma_public_api import LivumaPublicApi
    api = LivumaPublicApi()
    result = api.search_listings(offer="rent", property_type="villa", area="canggu",
                                 max_price=30_000_000, currency="IDR", price_period="monthly")
    for item in result["items"]:
        print(item["title"], item["publicUrl"])

Rate limit: 60 requests per minute per IP. The client raises RateLimited on HTTP 429.
Licence: MIT (see ../LICENSE).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://livuma.com/api/public"
USER_AGENT = "livuma-public-api-example/1.0 (+https://github.com/Livuma/livuma-docs)"


class LivumaApiError(Exception):
    """HTTP 4xx/5xx with the API's error message when there is one."""

    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class RateLimited(LivumaApiError):
    """HTTP 429. Wait a minute and retry."""


class LivumaPublicApi:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # --- endpoints -----------------------------------------------------------------------------

    def search_listings(self, **params):
        """GET /listings/search. Parameter names are snake_case as in the docs
        (offer, property_type, ownership_type, area, area_radius_km, lat, lng, min_price,
        max_price, currency, price_period, check_in, check_out, min_rooms, amenities,
        page, page_size, exclude_ids). Lists are joined with commas."""
        return self._get("/listings/search", params)

    def get_listing(self, listing_id: str):
        """GET /listings/{id}."""
        return self._get(f"/listings/{urllib.parse.quote(listing_id)}")

    def knowledge(self, q: str, top_k: int | None = None):
        """GET /knowledge?q=...&top_k=..."""
        return self._get("/knowledge", {"q": q, "top_k": top_k})

    def master_data(self):
        """GET /master-data. Call once and cache."""
        return self._get("/master-data")

    def market_stats(self):
        """GET /market-stats. Attribute as 'according to Livuma listing data'."""
        return self._get("/market-stats")

    # --- plumbing ------------------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None):
        query = {}
        for key, value in (params or {}).items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                value = ",".join(str(v) for v in value)
            query[key] = value
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(body).get("error", body)
            except ValueError:
                message = body
            if error.code == 429:
                raise RateLimited(error.code, message or "rate limited") from None
            raise LivumaApiError(error.code, message) from None


def _demo():
    api = LivumaPublicApi()
    print("Property types:", ", ".join(api.master_data()["propertyTypes"]))

    result = api.search_listings(
        offer="rent", property_type="villa", area="canggu", min_rooms=2,
        max_price=30_000_000, currency="IDR", price_period="monthly", page_size=3,
    )
    print(f"\n{result['total']} villas match; first {len(result['items'])}:")
    for item in result["items"]:
        monthly = item.get("priceMonthlyIdr")
        price = f"Rp {monthly:,.0f}/month" if monthly else "price on request"
        print(f"  {item['title']}  {price}  {item['publicUrl']}")

    answer = api.knowledge("is there a guest service fee?", top_k=1)
    if answer["items"]:
        print("\nKnowledge base:", answer["items"][0]["title"])

    stats = api.market_stats()
    canggu = next((r for r in stats["longTermRentals"] if r["areaSlug"] == "canggu"), None)
    if canggu:
        print(f"\nMedian monthly rent in Canggu ({stats['latestPeriod']}): Rp {canggu['median']:,.0f}"
              f" across {canggu['listings']} listings, according to Livuma listing data.")


if __name__ == "__main__":
    try:
        _demo()
    except LivumaApiError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
