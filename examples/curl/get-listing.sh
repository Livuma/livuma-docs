#!/usr/bin/env sh
# Full public details for one listing. Pass the GUID from a search result's "id" field.
LISTING_ID="${1:?usage: get-listing.sh <listing-guid>}"
curl -s "https://livuma.com/api/public/listings/${LISTING_ID}" \
  -H "Accept: application/json"
