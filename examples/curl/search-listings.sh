#!/usr/bin/env sh
# Search Livuma's live inventory: 2+ bedroom villas for rent in Canggu or Ubud,
# up to IDR 30,000,000 per month, with a pool. No API key needed.
curl -s "https://livuma.com/api/public/listings/search?offer=rent&property_type=villa&area=canggu,ubud&min_rooms=2&max_price=30000000&currency=IDR&price_period=monthly&amenities=pool&page_size=5" \
  -H "Accept: application/json"
