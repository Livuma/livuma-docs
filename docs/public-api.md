# Public API (no authentication)

A free, read-only JSON API over Livuma's live Bali listing inventory, public knowledge base and
monthly market statistics. It is built for AI agents, assistants and anyone who wants to search
Bali rentals or property programmatically without an account.

- Base URL: `https://livuma.com/api/public`
- Authentication: none
- Format: JSON (`application/json`), UTF-8
- Rate limit: **60 requests per minute per IP address**, shared with the [MCP server](mcp-server.md).
  Above that you receive HTTP `429`. Wait a minute and retry.
- Read-only: search, listing detail and availability quoting. Reserving is always completed by the
  guest in their own browser — the card authorisation, its 3-D Secure step and identity
  verification cannot be performed through the API. Every listing result carries a `url` on
  livuma.com to send people to, and `/listings/{id}/availability` returns a `bookingUrl` that opens
  the listing with the quoted dates selected.

The same query layer powers the MCP server, so parameters and results are identical there.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/listings/search` | Search the live inventory (rentals and sales) |
| `GET` | `/listings/{id}` | Full public details for one listing |
| `GET` | `/listings/{id}/availability` | Whether a stay can be booked, at which rate and for how much |
| `GET` | `/knowledge` | Natural-language search over Livuma's FAQs and policies |
| `GET` | `/master-data` | Valid values for the search parameters |
| `GET` | `/market-stats` | Monthly Bali rental and sale price statistics per area |

---

## `GET /listings/search`

Search the live listing inventory.

```
https://livuma.com/api/public/listings/search?offer=rent&property_type=villa&area=canggu&max_price=30000000
```

### Query parameters

All parameters are optional. Names are `snake_case`.

| Parameter | Type | Notes |
|---|---|---|
| `offer` | `rent` \| `sale` | Omit for both. |
| `property_type` | string | Property type name, e.g. `villa`, `apartment`. Valid values from `/master-data`. Case-insensitive, partial match allowed. |
| `ownership_type` | string | Sales only, e.g. `freehold`. Valid values from `/master-data`. |
| `area` | string | **One** area name, e.g. `canggu`. Free text: any Bali area name is geocoded server-side. To cover several areas, make one request per area — each then has its own correct `total` and ordering. |
| `area_radius_km` | number | Radius around the area or the coordinates. Default 10, max 20. Narrow it for exact-area results. |
| `lat`, `lng` | number | Coordinate-based location filter in decimal degrees. Must be given together. Alternative to `area`. |
| `min_price`, `max_price` | number | Budget in `currency`, compared against the price shown for this search: the stay **total** when `check_in` and `check_out` are given, otherwise the monthly rate (yearly in yearly mode) or the asking price for sales. |
| `currency` | `IDR` \| `USD` \| `EUR` | Default `IDR`. |
| `rental_mode` | `dates` \| `open_ended` \| `yearly` | How a rental stay is priced and filtered. `dates` (default): give `check_in` + `check_out`, or neither to browse monthly rates. `open_ended`: `check_in` only, monthly rate, no end date. `yearly`: `check_in` only, fixed 12-month term. |
| `check_in`, `check_out` | `yyyy-MM-dd` | When both are given, each result is priced for that exact stay and listings that don't meet the minimum stay are excluded. Omit `check_out` for `open_ended` and `yearly`. |
| `min_rooms` | integer | Minimum number of bedrooms. |
| `amenities` | string | Comma-separated amenity names, e.g. `pool,wifi,pet_friendly`. Valid values from `/master-data`. |
| `page` | integer | 1-based page number. |
| `page_size` | integer | 1 to 100, default 20. Raise it for bulk retrieval instead of paging. |
| `exclude_ids` | string | Comma-separated listing GUIDs to leave out, e.g. results already shown. |
| `include_insights` | boolean | Include AI-extracted photo and description insights. Off by default — they are large. |

### Response

Results are the same listings, in the same order, at the same prices as the search page on
livuma.com.

```json
{
  "items": [
    {
      "id": "5f094823-4516-4407-b59f-8ca8cdeb113a",
      "publicId": 3911,
      "url": "https://livuma.com/s/3911/villa-2-bedroom-in-canggu-babakan",
      "title": "VILLA 2 BEDROOM IN CANGGU, BABAKAN",
      "area": "80351, Kuta Utara",
      "latitude": -8.6392,
      "longitude": 115.1362,
      "propertyType": "Villa",
      "offer": "rent",
      "bedrooms": 2,
      "bathrooms": 2,
      "imageUrl": "https://cdn.livuma.com/cdn-cgi/image/width=1280,quality=92,f=auto/listings/.../photo.webp",
      "price": {
        "currency": "IDR",
        "amount": 24000000.0,
        "period": "monthly",
        "formatted": "Rp 24M"
      },
      "rates": {
        "currency": "IDR",
        "monthly": 24000000.0,
        "yearly": 288000000.0,
        "minimumStayMonths": 1
      },
      "averageRating": 4.8,
      "reviewCount": 12,
      "amenities": ["pool", "wifi", "parking"],
      "isBookable": true,
      "hostIsVerified": true
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 446,
  "hasMore": true,
  "filteredAfterPaging": false,
  "resolvedArea": "canggu"
}
```

Notes on the item shape:

- `id` is the listing GUID to pass to `/listings/{id}`. `url` is the canonical page to send people
  to; `publicId` is the short id used in `/s/{id}` links.
- `price` is the price for **this** search: with `check_in` + `check_out` it is the total for that
  exact stay (`period: "total"`, plus `nights`/`months`, `rateUsed` and `effectiveNightlyRate` for
  a nightly stay); otherwise it is the per-period rate the search browsed on.
- `rates` carries the host's published rates and minimum stays, converted into `currency`.
- `imageUrl` is the listing's primary photo, as the website itself renders it.
- `isBookable` is `false` when the listing is discovery-only right now — a sales listing, or a host
  who has not finished activating their payout account. Do not promise a booking for one.
- `amenities` lists the amenity names the listing actually has, using the same vocabulary you
  filter with.
- `averageRating` (1 to 5) and `reviewCount` come from verified, platform-booked stays only.
- `resolvedArea` echoes the area the server matched, and `areaIsKnown` says how: `true` means one
  of Bali's known areas, so the location filter is exact. `false` means the name was geocoded as
  free text — the geocoder biases every query to Bali, so a typo or an unknown place still matches
  a plausible-looking point somewhere on the island. Check each item's `area` before telling anyone
  where a listing is.
- An area that cannot be located at all returns an **empty page** with `unresolvedArea` set. The
  search is never silently run without the location filter.

#### Paging

`total` is the number of listings matching the database filters, and is the paging authority.

When `filteredAfterPaging` is `true`, the exact per-stay price was applied **after** the database
paged the results — so a short page is **not** the end of the results. Keep requesting pages while
`hasMore` is `true`.

#### Changed parameters

Two parameters were renamed in September 2026. Requests still using the old names get an HTTP `400`
that names the replacement, rather than silently answering a different question:

| Old | Now |
|---|---|
| `price_period=monthly` | the default — omit it, or `rental_mode=dates` |
| `price_period=yearly` | `rental_mode=yearly` |
| `price_period=daily` | no equivalent: pass `check_in` + `check_out`, and `max_price` then applies to the stay total |
| `area=canggu,ubud` | one area per request: `area=canggu`, then `area=ubud` |

### Errors

Invalid parameters return HTTP `400` with a message you can show or act on:

```json
{ "error": "Invalid 'currency'. Supported: IDR, USD, EUR." }
```

Unknown `property_type`, `ownership_type` and `amenities` values are rejected the same way, and the
message lists the valid values.

---

## `GET /listings/{id}`

Everything the public listing page shows for one listing. `{id}` accepts the GUID `id` from search
results or the short id from a `/s/{id}` link.

```
https://livuma.com/api/public/listings/5f094823-4516-4407-b59f-8ca8cdeb113a
https://livuma.com/api/public/listings/3911?check_in=2026-11-01&check_out=2026-11-20
```

| Parameter | Type | Notes |
|---|---|---|
| `currency` | `IDR` \| `USD` \| `EUR` | Default `IDR`. |
| `check_in`, `check_out` | `yyyy-MM-dd` | Adds a live quote for the stay under `availability`. |
| `rental_mode` | `dates` \| `open_ended` \| `yearly` | Default `dates`. |

The response wraps the search item as `listing` and adds:

- `description` and `images` (the photo gallery, CDN renditions)
- `includedServices` — what the host includes in the rent (cleaning, pool service, gardener)
- `host` — first name, `isVerified` and `isActivated` (payout account ready). No contact details:
  guests reach hosts through Livuma's in-app chat after booking.
- `seasonalRates` — per-night pricing for specific date ranges, where the host has set any
- `reviews` — `averageRating`, `reviewCount` and the latest published guest reviews
- `bookedRanges` — the booked/blocked calendar as `{ from, to }` date windows (`to: null` means
  blocked indefinitely). Dates only: why a window is blocked is not published.
- `availability` — present when `check_in` was given; identical in shape to the endpoint below

Unknown, paused and removed listings all return HTTP `404` with the same body, so listing ids
cannot be probed for existence:

```json
{ "error": "not_found" }
```

---

## `GET /listings/{id}/availability`

Whether a stay can be booked, at which rate and for how much — the same answer the listing page
gives a visitor. **Check here before telling anyone dates are free:** search filters on
availability, but only this confirms a rate, the exact price and the payment schedule.

```
https://livuma.com/api/public/listings/3911/availability?check_in=2026-11-01&check_out=2026-11-20
```

| Parameter | Type | Notes |
|---|---|---|
| `check_in` | `yyyy-MM-dd` | **Required.** |
| `check_out` | `yyyy-MM-dd` | Omit for `open_ended` and `yearly`. |
| `rental_mode` | `dates` \| `open_ended` \| `yearly` | Default `dates`. |

```json
{
  "listingId": "5f094823-4516-4407-b59f-8ca8cdeb113a",
  "checkIn": "2026-11-01",
  "checkOut": "2026-11-20",
  "available": true,
  "recommendedRate": "daily",
  "options": [
    {
      "rate": "daily",
      "offered": true,
      "eligible": true,
      "nights": 19,
      "currency": "IDR",
      "ratePerPeriod": 1200000.0,
      "firstPaymentAmount": 22800000.0,
      "firstPaymentDueDate": "2026-10-20",
      "cancellation": { "freeCancelDays": 7, "minimumStayDays": 3 }
    },
    {
      "rate": "monthly",
      "offered": true,
      "eligible": false,
      "reason": "minimum_stay",
      "reasonText": "This rate has a minimum stay of 3 months."
    }
  ],
  "bookedRanges": [{ "from": "2026-12-01", "to": "2026-12-10" }],
  "bookingUrl": "https://livuma.com/s/3911/villa?checkIn=2026-11-01&checkOut=2026-11-20"
}
```

- Each entry in `options` covers one rate and says whether the host offers it, whether it is
  `eligible` for these dates, and if not, why. Eligible options carry `nights`/`months`,
  `ratePerPeriod`, `firstPaymentAmount`, `firstPaymentDueDate`, the full `paymentSchedule` and the
  `cancellation` terms.
- `quotedCheckOut` on an option is the move-out that option actually prices to, which can differ
  from the one you asked for: a **yearly rate is always exactly one year**, so an 18-month request
  is quoted — and would be booked — as twelve months. The figures on the option belong to
  `quotedCheckOut`, and `bookingUrl` opens those dates, not the requested ones.
- Livuma charges guests no service fee, so the amounts shown are what the guest pays.
- When the whole listing cannot be booked, `available` is `false` and `reason` says why:
  `not_a_rental`, `host_not_activated`, `currency_not_supported`, `dates_unavailable`,
  `open_ended_unavailable` or `no_eligible_rate`. `reasonText` is the same thing in plain English.
- **To book, send the user to `bookingUrl`** — it opens the listing with these dates selected.
  Reserving cannot be done through this API: the card authorisation, its 3-D Secure step and
  identity verification all happen in the guest's own browser.

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
