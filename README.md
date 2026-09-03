# Livuma developer documentation

[Livuma](https://livuma.com) is Bali's marketplace for long-term rentals and property, built as an
alternative to Airbnb and Booking.com for people who stay for months, not nights. Hosts pay about
half the commission of the big platforms and only on completed bookings; guests pay zero fees and
see one transparent price. Monthly and yearly stays run on automated recurring rent, digital rental
agreements and KYC-verified profiles, with AI handling listing moderation, customer support and
notifications.

This repository documents the machine interfaces around that marketplace: a public, key-free
search API and MCP server for AI agents, and the authenticated Listing and Booking APIs that hosts
and agencies use to run their inventory from their own systems. Livuma is operated by
PT Livuma Home Market, Badung, Bali.

## Contents

| Document | What it covers | Auth |
|---|---|---|
| [Public API](docs/public-api.md) | Search live listings, listing details, knowledge search, search-parameter values, monthly market statistics. JSON over `https://livuma.com/api/public`. | none |
| [MCP server](docs/mcp-server.md) | The same search as native tool calls for Claude, Cursor and any MCP client. `https://livuma.com/mcp`. | none |
| [Listing API](docs/listing-api.md) | Create, update, pause and remove your own listings, upload photos. `https://livuma.com/api/v1/listings`. | API key |
| [Booking API](docs/booking-api.md) | Read and answer booking requests on your listings, cancellation preview, guest chat. `https://livuma.com/api/v1/bookings`. | API key |

Examples live in [`examples/`](examples/): curl calls for every public endpoint, a
dependency-free Python client, and MCP client configuration snippets.

## Quick start

Search two-bedroom villas in Canggu under Rp 30,000,000 a month, no key needed:

```bash
curl "https://livuma.com/api/public/listings/search?offer=rent&property_type=villa&area=canggu&max_price=30000000&price_period=monthly&min_rooms=2"
```

Give Claude Code the same search as a tool:

```bash
claude mcp add --transport http livuma https://livuma.com/mcp
```

Every result carries a `publicUrl` on livuma.com. Booking requests are always made there by the
user; the public interfaces are read-only.

## Related

- Website: https://livuma.com
- Bali rental market data (monthly medians per area, citable): https://livuma.com/bali-rental-prices
  and the [bali-rental-market-data](https://github.com/Livuma/bali-rental-market-data) repository
- Real estate SaaS for agencies (listings, CRM, booking engine, AI marketing):
  https://livuma.com/real-estate-solution
- Plain-language platform description for AI assistants: https://livuma.com/llms.txt

## Rate limits at a glance

| Interface | Limit | Over the limit |
|---|---|---|
| Public API and MCP server | 60 requests / minute / IP | HTTP `429`, retry after a minute |
| Listing and Booking API | 120 requests / minute / key | HTTP `429` with `Retry-After` |

## Support

- Documentation issues: open an issue in this repository (see [CONTRIBUTING](CONTRIBUTING.md)).
- API access, keys, listings and bookings: hello@livuma.com or the WhatsApp support link in the
  docs.
- Security reports: see [SECURITY.md](SECURITY.md).

## License

Documentation is licensed under [CC BY 4.0](LICENSE). The code in `examples/` is released under the
MIT License (see the note at the end of [LICENSE](LICENSE)). Livuma and the Livuma logo are
trademarks of PT Livuma Home Market.
