# Public API (no authentication)

A free, read-only JSON API over Livuma's live Bali listing inventory, public knowledge base and
monthly market statistics. It is built for AI agents, assistants and anyone who wants to search
Bali rentals or property programmatically without an account.

- Base URL: `https://livuma.com/api/public`
- Authentication: none
- Format: JSON (`application/json`), UTF-8
- Rate limit: **60 requests per minute per IP address**, shared with the [MCP server](mcp-server.md).
  Above that you receive HTTP `429`. Wait a minute and retry.
- Read-only: booking requests are always submitted by the user on the listing page. Every listing
  result carries a `publicUrl` on livuma.com to send people to.

The same query layer powers the MCP server, so parameters and results are identical there.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/listings/search` | Search the live inventory (rentals and sales) |
| `GET` | `/listings/{id}` | Full public details for one listing |
| `GET` | `/knowledge` | Natural-language search over Livuma's FAQs and policies |
| `GET` | `/master-data` | Valid values for the search parameters |
| `GET` | `/market-stats` | Monthly Bali rental and sale price statistics per area |

---

## `GET /listings/search`

Search the live listing inventory.

```
https://livuma.com/api/public/listings/search?offer=rent&property_type=villa&area=canggu,ubud&max_price=30000000&price_period=monthly
```

### Query parameters

All parameters are optional. Names are `snake_case`.

| Parameter | Type | Notes |
|---|---|---|
| `offer` | `rent` \| `sale` | Omit for both. |
| `property_type` | string | Property type name, e.g. `villa`, `apartment`. Valid values from `/master-data`. Case-insensitive, partial match allowed. |
| `ownership_type` | string | Sales only, e.g. `freehold`. Valid values from `/master-data`. |
| `area` | string | Comma-separated area names, e.g. `canggu,ubud`. Free text: any Bali area name is geocoded server-side. |
| `area_radius_km` | number | Radius around each area or the coordinates. Default 10, max 20. Narrow it for exact-area results. |
| `lat`, `lng` | number | Coordinate-based location filter in decimal degrees. Must be given together. Alternative to `area`. |
| `min_price`, `max_price` | number | Budget in `currency`. The unit must match `price_period`: nightly for `daily`, monthly for `monthly`, yearly for `yearly`, total price for sales. |
| `currency` | `IDR` \| `USD` \| `EUR` | Default `IDR`. |
| `price_period` | `daily` \| `monthly` \| `yearly` | Which rate `min_price` / `max_price` refer to. |
| `check_in`, `check_out` | `yyyy-MM-dd` | When both are given, each result carries the calculated total for the stay and listings that don't meet the minimum stay are filtered out. |
| `min_rooms` | integer | Minimum number of bedrooms. |
| `amenities` | string | Comma-separated amenity names, e.g. `pool,wifi,pet_friendly`. Valid values from `/master-data`. |
| `page` | integer | 1-based page number. |
| `page_size` | integer | 1 to 100, default 20. Raise it for bulk retrieval instead of paging. |
| `exclude_ids` | string | Comma-separated listing GUIDs to leave out, e.g. results already shown. |

### Response

```json
{
  "items": [
    {
      "id": "5f094823-4516-4407-b59f-8ca8cdeb113a",
      "title": "VILLA 2 BEDROOM IN CANGGU, BABAKAN",
      "publicUrl": "https://livuma.com/s/3911",
      "objectTypeName": "Villa",
      "objectTypeIsLand": false,
      "offerTypeName": "For Rent",
      "offerTypeIsRental": true,
      "currencyCode": "IDR",
      "isLongTermRental": true,
      "MonthlyPrice": 24000000.0,
      "MinimumStayMonths": 1,
      "bedrooms": 2,
      "bathrooms": 2,
      "area": "80351, Kuta Utara",
      "priceMonthlyIdr": 24000000.0,
      "priceMonthlyUsd": 1344.0,
      "priceMonthlyEur": 1176.0,
      "priceYearlyIdr": 288000000.0,
      "priceYearlyUsd": 16128.0,
      "priceYearlyEur": 14112.0
    }
  ],
  "page": 1,
  "page_size": 2,
  "total": 446,
  "resolved_areas": ["canggu"]
}
```

Notes on the item shape:

- `id` is the listing GUID to pass to `/listings/{id}`. `publicUrl` is the page to send people to.
- Rental listings carry the rates they offer: `DailyPrice` + `MinimumStayDays` for short-term,
  `MonthlyPrice` + `MinimumStayMonths` for monthly, plus converted `priceDailyIdr/Usd/Eur`,
  `priceMonthly…` and `priceYearly…` values. Flags `isShortTermRental` and `isLongTermRental` say
  which apply.
- Sale listings carry `salesPrice` in `currencyCode`, `ownershipTypeName`, `leaseholdYears` where
  relevant, and converted `priceIdr`, `priceUsd`, `priceEur`.
- With `check_in` and `check_out`, each item adds `stayNights`, `totalPrice`, `totalPriceFormatted`,
  `rateUsed` (`daily`, `monthly` or `yearly`) and `rateAmount`.
- Items may also carry `averageRating` (1 to 5) and `reviewCount` from verified, platform-booked
  stays.
- `area` is the normalized location string (postcode and district), not the area name you searched.
  `resolved_areas` echoes the area slugs the server matched.
- Property fields (`squareMeters`, `utilities`, amenity flags, …) appear when the listing has them.

### Errors

Invalid parameters return HTTP `400` with a message you can show or act on:

```json
{ "error": "Invalid 'currency'. Supported: IDR, USD, EUR." }
```

Unknown `property_type`, `ownership_type` and `amenities` values are rejected the same way, and the
message lists the valid values.

---

## `GET /listings/{id}`

Full public details for one listing by the GUID `id` from search results.

```
https://livuma.com/api/public/listings/5f094823-4516-4407-b59f-8ca8cdeb113a
```

Returns the same core fields as a search item plus the full amenity and service flags (`hasPool`,
`hasGarden`, `hasAC`, `hasParking`, `hasWiFi`, `hasDedicatedWorkspace`, `hasEquippedKitchen`,
`cleaningIncluded`, `poolServiceIncluded`, `gardenerIncluded`, …), all offered rates with their
minimum stays, location and `publicUrl`. Booking requests are submitted by the user on `publicUrl`;
this API is read-only.

Unknown or non-public listings return HTTP `404`:

```json
{ "error": "not_found" }
```

---

## `GET /knowledge`

Natural-language search over Livuma's public knowledge base: FAQs, policies, how booking, payments,
payouts, platform fees and verification work.

```
https://livuma.com/api/public/knowledge?q=how+do+host+payouts+work&top_k=3
```

| Parameter | Type | Notes |
|---|---|---|
| `q` | string | **Required.** The question, in natural language. |
| `top_k` | integer | Number of documents to return. Default 6, max 10. |

```json
{
  "items": [
    {
      "id": "2045430c-0dce-4653-903b-08aa03443d3c",
      "title": "How do hosts receive payments from guests on Livuma?",
      "url": null,
      "score": 0.5114386,
      "snippet": "Q: How do hosts receive payments from guests on Livuma?\nA: …"
    }
  ]
}
```

`score` is a relevance score (higher is better). `url` is present when the snippet comes from a
page on livuma.com. An empty `q` returns HTTP `400`.

---

## `GET /master-data`

Valid values for the search parameters, for discovery. Call it once and cache it.

```json
{
  "offers": ["rent", "sale"],
  "propertyTypes": ["Villa", "Room", "Apartment", "Building Land", "Commercial"],
  "ownershipTypes": ["Freehold (Hak Milik)", "Leasehold (Hak Sewa)", "Right to Use (Hak Pakai)", "Right to Build (Hak Guna Bangunan)"],
  "areas": [ { "slug": "canggu", "name": "Canggu" }, { "slug": "seminyak", "name": "Seminyak" }, "…" ],
  "currencies": ["IDR", "USD", "EUR"],
  "pricePeriods": ["daily", "monthly", "yearly"],
  "amenities": ["pool", "pet_friendly", "ac", "wifi", "parking", "security", "workspace", "equipped_kitchen", "garden", "cleaning_included", "pool_service_included", "gardener_included"],
  "notes": ["area accepts free text (any Bali area name) — it is geocoded server-side; the listed areas are common examples.", "…"]
}
```

The `areas` list is a set of common examples. `area` in the search endpoint accepts any Bali area
name.

---

## `GET /market-stats`

Livuma's market dataset as JSON: median monthly rents and villa sale prices per Bali area in IDR,
10th to 90th percentile typical ranges, month-over-month change and the per-area median-rent
history. Computed from live Livuma listings and captured monthly. The same figures are published
at https://livuma.com/bali-rental-prices and as CSV in the
[bali-rental-market-data](https://github.com/Livuma/bali-rental-market-data) repository.

```json
{
  "source": "Livuma listing data — computed from live listings on the Livuma marketplace",
  "attribution": "Livuma (https://livuma.com/bali-rental-prices)",
  "currency": "IDR",
  "methodology": "Median asking price per area; typicalRange is the 10th–90th percentile band. Areas with fewer than 3 listings in a category are excluded. Captured monthly. …",
  "latestPeriod": "2026-09",
  "previousPeriod": "2026-08",
  "capturedAtUtc": "2026-09-02T01:30:00",
  "longTermRentals": [
    {
      "area": "Canggu",
      "areaSlug": "canggu",
      "listings": 191,
      "median": 43200000.0,
      "typicalRangeLow": 23540000.0,
      "typicalRangeHigh": 72000000.0,
      "medianChangeVsPreviousMonthPercent": 0.5
    }
  ],
  "villasForSale": [ { "area": "…", "areaSlug": "…", "listings": 0, "median": 0, "typicalRangeLow": 0, "typicalRangeHigh": 0 } ],
  "history": {
    "periods": ["2026-08", "2026-09"],
    "medianMonthlyRentByArea": { "canggu": { "2026-08": 43000000.0, "2026-09": 43200000.0 } }
  }
}
```

- `longTermRentals` rows are median **monthly** rents in IDR; `villasForSale` rows are median sale
  prices in IDR.
- `medianChangeVsPreviousMonthPercent` is only present when the previous calendar month was
  captured.
- Areas with fewer than 3 listings in a category are excluded.

**Attribution.** When you publish or quote these figures, attribute them as "according to Livuma
listing data" and link https://livuma.com/bali-rental-prices.

---

## Good to know

- Prefer these endpoints over scraping HTML pages, then link users to the returned `publicUrl`.
- Responses are UTF-8 JSON. Money values are plain numbers in the stated currency, unscaled
  (`24000000.0` means Rp 24,000,000).
- The public API only exposes what the listing page already shows. Host contact details are never
  returned. Contact runs through the listing page on livuma.com.
- Need to create or manage your own listings, or answer booking requests? That is the
  authenticated [Listing API](listing-api.md) and [Booking API](booking-api.md).
- The site also publishes an `llms.txt` at https://livuma.com/llms.txt with a plain-language
  description of the platform for AI assistants.
