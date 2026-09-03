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
| Scope | Read-only search and discovery. Booking requests are submitted by the user on the listing page (`publicUrl` in every result). |

The tools wrap the same query layer as the REST API, so parameters, values and results match
`https://livuma.com/api/public`.

## Tools

### `search_listings`

Search Livuma's live Bali rental and property-sale inventory. Returns JSON
`{ items, page, page_size, total, resolved_areas }`. Each item includes `id` (GUID), `title`,
`publicUrl` (direct link on livuma.com for the user), prices in IDR, USD and EUR, rooms and
amenities. When `checkInDate` and `checkOutDate` are given, each item also carries the calculated
total price for the stay (`stayNights`, `totalPrice`, `rateUsed`, `rateAmount`) and listings that
don't meet the minimum stay are filtered out. Call `get_search_options` first if unsure about valid
property types, areas or amenities. For "more results", increment `page`.

All parameters are optional.

| Parameter | Type | Description |
|---|---|---|
| `offer` | string | `"rent"` or `"sale"`. Omit for both. |
| `propertyType` | string | Property type name, e.g. `"Villa"`, `"Apartment"`. Valid values from `get_search_options`. |
| `ownershipType` | string | Ownership type for sales, e.g. `"Freehold"`. Omit for rentals. |
| `areas` | string[] | Area names, e.g. `["Canggu", "Ubud"]`. Free text, geocoded server-side. |
| `areaRadiusKm` | number | Search radius in km around each area or the coordinates. Default 10, max 20. Narrow for exact-area results. |
| `latitude`, `longitude` | number | Coordinate-based location filter (decimal degrees). Use both together; alternative to `areas`. |
| `minPrice`, `maxPrice` | number | Budget in `currency`. Unit must match `pricePeriod`: nightly for daily, monthly for monthly, yearly for yearly, total for sales. |
| `currency` | string | `"IDR"` (default), `"USD"` or `"EUR"`. |
| `pricePeriod` | string | `"daily"`, `"monthly"` or `"yearly"`: which rate the price bounds refer to. |
| `checkInDate`, `checkOutDate` | string | `yyyy-MM-dd`. |
| `minRooms` | integer | Minimum number of bedrooms. |
| `amenities` | string[] | e.g. `["pool", "wifi", "pet_friendly"]`. Valid values from `get_search_options`. |
| `page` | integer | 1-based page number. |
| `pageSize` | integer | Results per page, 1 to 100 (default 20). Raise it for bulk retrieval instead of paging. |
| `excludeIds` | string[] | Listing GUIDs to exclude, e.g. results already shown to the user. |

Example call:

```json
{
  "name": "search_listings",
  "arguments": {
    "offer": "rent",
    "propertyType": "Villa",
    "areas": ["Canggu"],
    "maxPrice": 30000000,
    "currency": "IDR",
    "pricePeriod": "monthly",
    "minRooms": 2,
    "amenities": ["pool", "wifi"],
    "pageSize": 5
  }
}
```

Parameter mistakes come back as content the model can act on, not as protocol errors:

```json
{ "error": "Unknown property_type \"Bungalow\". Valid values: Villa, Room, Apartment, Building Land, Commercial." }
```

### `get_listing_details`

Full public details for one listing: all rates and minimum stays, amenities and included services,
location, and the `publicUrl` to send the user to. Read-only.

| Parameter | Type | Description |
|---|---|---|
| `listingId` | string | **Required.** The listing GUID from search results (field `id`). |

```json
{ "name": "get_listing_details", "arguments": { "listingId": "5f094823-4516-4407-b59f-8ca8cdeb113a" } }
```

An unknown id returns `{ "error": "not_found" }`.

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
common areas (slug + name), currencies, price periods and amenity names, plus short usage notes.
Call it once per session and reuse the result.

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
