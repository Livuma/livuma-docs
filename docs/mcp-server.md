# Livuma MCP server

Livuma runs a public [Model Context Protocol](https://modelcontextprotocol.io) server so AI
assistants can search Bali's live rental and property inventory natively, as tool calls instead of
web scraping.

| | |
|---|---|
| Endpoint | `https://livuma.com/mcp` |
| Transport | Streamable HTTP, stateless (no session to keep alive) |
| Authentication | None |
| Server name | `livuma` (title: "Livuma Homes Market — Bali rental & property search") |
| Rate limit | 60 requests per minute per IP address, shared with the [public REST API](public-api.md). Over the limit you get HTTP `429`; wait a minute and retry. |
| Scope | Read-only search, detail and availability quoting. Reserving is always completed by the guest in their own browser — the card authorisation, its 3-D Secure step and identity verification cannot be performed through the API. `check_availability` returns a `bookingUrl` that opens the listing with the quoted dates selected. |

The tools wrap the same query layer as the REST API, so parameters, values and results match
`https://livuma.com/api/public`.

## Tools

### `search_listings`

Search Livuma's live Bali rental and property-sale inventory — the same listings, in the same
order, at the same prices as the search page on livuma.com. Returns
`{ items, page, pageSize, total, hasMore, filteredAfterPaging, resolvedArea }`.

Each item includes `id` (GUID), `publicId`, `url` (the canonical link to send the user to),
`title`, `area`, `latitude`/`longitude`, `imageUrl` (the listing's primary photo), `price`
(the price for *this* search — the stay total when dates are given, otherwise the per-period
rate), `rates` (the host's published rates and minimum stays), `bedrooms`, `bathrooms`,
`amenities`, `averageRating`, `reviewCount` and `isBookable`.

`isBookable: false` means the listing is discovery-only right now — a sales listing, or a host who
has not finished activating their payout account. Do not promise a booking for one.

**Paging.** `total` is the number of listings matching the database filters, and is the paging
authority. When `filteredAfterPaging` is `true` the exact per-stay price was applied *after* the
database paged the results, so a short page is **not** the end of the results — keep requesting
pages while `hasMore` is `true`.

**Location.** `resolvedArea` echoes the area matched and `areaIsKnown` says how: `true` is one of
Bali's known areas and the filter is exact; `false` means the name was geocoded as free text, and
because the geocoder biases every query to Bali a typo still lands on a plausible point somewhere
on the island — check each item's `area`. An area that cannot be located at all returns an **empty
page** with `unresolvedArea` set, never an unfiltered island-wide search.

Call `get_search_options` first if unsure about valid property types, areas or amenities.

All parameters are optional.

| Parameter | Type | Description |
|---|---|---|
| `offer` | string | `"rent"` or `"sale"`. Omit for both. |
| `propertyType` | string | Property type name, e.g. `"Villa"`, `"Apartment"`. Valid values from `get_search_options`. |
| `ownershipType` | string | Ownership type for sales, e.g. `"Freehold"`. Omit for rentals. |
| `area` | string | **One** area name, e.g. `"Canggu"`. Free text, geocoded server-side. To cover several areas, call once per area — each call then has its own correct total and ordering. |
| `areaRadiusKm` | number | Search radius in km around the area or the coordinates. Default 10, max 20. Narrow for exact-area results. |
| `latitude`, `longitude` | number | Coordinate-based location filter (decimal degrees). Use both together; alternative to `area`. |
| `minPrice`, `maxPrice` | number | Budget in `currency`, compared against the price shown for this search: the stay **total** when `checkInDate` and `checkOutDate` are given, otherwise the monthly rate (yearly in yearly mode) or the asking price for sales. |
| `currency` | string | `"IDR"` (default), `"USD"` or `"EUR"`. |
| `rentalMode` | string | How a rental stay is priced and filtered. `"dates"` (default): give `checkInDate` + `checkOutDate`, or neither to browse monthly rates. `"open_ended"`: `checkInDate` only, monthly rate, no end date. `"yearly"`: `checkInDate` only, fixed 12-month term. |
| `checkInDate`, `checkOutDate` | string | `yyyy-MM-dd`. Omit `checkOutDate` for `open_ended` and `yearly`. |
| `minRooms` | integer | Minimum number of bedrooms. |
| `amenities` | string[] | e.g. `["pool", "wifi", "pet_friendly"]`. Valid values from `get_search_options`. |
| `page` | integer | 1-based page number. |
| `pageSize` | integer | Results per page, 1 to 100 (default 20). Raise it for bulk retrieval instead of paging. |
| `excludeIds` | string[] | Listing GUIDs to exclude, e.g. results already shown to the user. |
| `includeInsights` | boolean | Include AI-extracted photo and description insights. Off by default — they are large. |

Example call:

```json
{
  "name": "search_listings",
  "arguments": {
    "offer": "rent",
    "propertyType": "Villa",
    "area": "Canggu",
    "maxPrice": 30000000,
    "currency": "IDR",
    "minRooms": 2,
    "amenities": ["pool", "wifi"],
    "pageSize": 5
  }
}
```

Parameter mistakes come back as content the model can act on, not as protocol errors:

```json
{ "error": "Unknown property_type BUNGALOW. Valid values: Villa, Room, Apartment, Building Land, Commercial." }
```

### `get_listing_details`

Everything the public listing page shows for one listing: `description`, `images`, all rates and
minimum stays, `amenities` and `includedServices`, `seasonalRates` (per-night pricing for specific
date ranges), published guest `reviews`, `host` verification, the `bookedRanges` calendar, and the
canonical `url` to send the user to.

Pass `checkInDate` (and `checkOutDate`, or a `rentalMode`) to get a live availability quote in the
same call, under `availability` — identical in shape to `check_availability`.

| Parameter | Type | Description |
|---|---|---|
| `listingId` | string | **Required.** The listing `id` (GUID) from search results. The short id from a `/s/{id}` link, or the listing URL itself, also work. |
| `currency` | string | `"IDR"` (default), `"USD"` or `"EUR"`. |
| `checkInDate`, `checkOutDate` | string | `yyyy-MM-dd`. Adds a live quote for the stay. |
| `rentalMode` | string | `"dates"` (default), `"open_ended"` or `"yearly"`. |

```json
{ "name": "get_listing_details", "arguments": { "listingId": "5f094823-4516-4407-b59f-8ca8cdeb113a" } }
```

An unknown, paused or removed listing returns `{ "error": "listing_not_found" }` — all three answer
identically, so listing ids cannot be probed for existence.

### `check_availability`

Whether a listing can be booked for specific dates, at which rate and for how much — the same
answer the listing page gives a visitor. **Always check here before telling someone dates are
free:** search filters on availability, but only the quote confirms a rate, the exact price and the
payment schedule.

Returns `{ available, reason, reasonText, recommendedRate, options, bookedRanges, bookingUrl }`.

Each entry in `options` covers one rate (`daily`, `monthly`, `yearly`) and states whether the host
offers it, whether it is `eligible` for these dates, and if not, why — for example
`minimum_stay`, `stay_too_long_for_daily_rate` or `check_out_required`. An eligible option carries
`nights`/`months`, `ratePerPeriod`, `firstPaymentAmount`, `firstPaymentDueDate`, the full
`paymentSchedule` and the `cancellation` terms.

`quotedCheckOut` is the move-out that option actually prices to, which can differ from the one you
asked for: a **yearly rate is always exactly one year**, so an 18-month request is quoted — and
would be booked — as twelve months. The option's figures belong to `quotedCheckOut`, and
`bookingUrl` opens those dates rather than the requested ones.

Livuma charges guests no service fee, so the amounts shown are what the guest pays.

When the whole listing cannot be booked, `reason` says why: `not_a_rental`, `host_not_activated`,
`currency_not_supported`, `dates_unavailable`, `open_ended_unavailable` or `no_eligible_rate`.

**To book, send the user to `bookingUrl`.** It opens the listing with these dates selected.
Reserving cannot be done through this API: the card authorisation, its 3-D Secure step and identity
verification all happen in the guest's own browser.

| Parameter | Type | Description |
|---|---|---|
| `listingId` | string | **Required.** The listing `id` (GUID), a short `/s/{id}` id, or the listing URL. |
| `checkInDate` | string | **Required.** `yyyy-MM-dd`. |
| `checkOutDate` | string | `yyyy-MM-dd`. Omit for `open_ended` and `yearly`. |
| `rentalMode` | string | `"dates"` (default), `"open_ended"` (no end date, monthly) or `"yearly"` (fixed 12-month term). |

```json
{
  "name": "check_availability",
  "arguments": {
    "listingId": "5f094823-4516-4407-b59f-8ca8cdeb113a",
    "checkInDate": "2026-11-01",
    "checkOutDate": "2026-11-20"
  }
}
```

### `search_knowledge`

Search Livuma's public knowledge base (FAQs, policies, how booking, payments and payouts work,
platform fees, verification) by natural-language question. Returns ranked snippets with `title`,
`score`, `snippet` and a source `url` where one exists.

| Parameter | Type | Description |
|---|---|---|
| `query` | string | **Required.** Natural-language question, e.g. `"how do host payouts work?"` |
| `topK` | integer | Number of documents to return. Default 6, max 10. |

```json
{ "name": "search_knowledge", "arguments": { "query": "is there a guest service fee?", "topK": 3 } }
```

### `get_search_options`

No parameters. Lists valid values for `search_listings`: offers, property types, ownership types,
common areas (slug + name), currencies, rental modes and amenity names, plus notes on how paging,
budgets and bookability work. Call it once per session and reuse the result.

## Connecting a client

### Claude Code

```bash
claude mcp add --transport http livuma https://livuma.com/mcp
```

Then ask, for example: "Find me a 2-bedroom villa in Canggu under 30 million IDR a month with a
pool, and show the links."

### Claude Desktop

Add Livuma as a custom connector: **Settings → Connectors → Add custom connector**, name `Livuma`,
URL `https://livuma.com/mcp`. No OAuth or key is needed.

If your Claude Desktop build only reads `claude_desktop_config.json` with local commands, bridge the
remote server with `mcp-remote`:

```json
{
  "mcpServers": {
    "livuma": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://livuma.com/mcp"]
    }
  }
}
```

### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "livuma": {
      "url": "https://livuma.com/mcp"
    }
  }
}
```

### Any other MCP client

Use the streamable-HTTP transport with URL `https://livuma.com/mcp` and no credentials. Ready-made
snippets are in [`examples/mcp-config/`](../examples/mcp-config/).

### Raw protocol check

A quick way to confirm the server answers, without an MCP client (the response is a JSON-RPC
message; the `Accept` header must allow both JSON and an event stream):

```bash
curl -s https://livuma.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Guidance for assistants

- Prefer the tools over scraping livuma.com, then link the user to `publicUrl` to view details and
  submit a booking request.
- Price bounds must be in the unit of `pricePeriod`. A "30 million a month" budget is
  `maxPrice: 30000000, currency: "IDR", pricePeriod: "monthly"`.
- When the user has dates, pass `checkInDate` and `checkOutDate` so results carry the exact stay
  total and honour minimum stays.
- Livuma's own plain-language description for AI assistants is at https://livuma.com/llms.txt.
- Questions about the platform itself (fees, payouts, verification, cancellations) belong in
  `search_knowledge`, not in the user's head or yours.
