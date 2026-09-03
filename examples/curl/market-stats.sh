#!/usr/bin/env sh
# Monthly Bali rental and villa sale price statistics per area (IDR).
# Attribute as "according to Livuma listing data" and link https://livuma.com/bali-rental-prices
curl -s "https://livuma.com/api/public/market-stats" -H "Accept: application/json"
