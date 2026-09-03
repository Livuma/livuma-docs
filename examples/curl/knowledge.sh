#!/usr/bin/env sh
# Ask Livuma's public knowledge base a question in plain language.
QUESTION="${1:-how do host payouts work}"
curl -s -G "https://livuma.com/api/public/knowledge" \
  --data-urlencode "q=${QUESTION}" \
  --data-urlencode "top_k=3" \
  -H "Accept: application/json"
