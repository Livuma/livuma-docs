#!/usr/bin/env sh
# Raw protocol check of the MCP server without an MCP client: list the available tools.
# The Accept header must allow both JSON and an event stream (streamable HTTP transport).
curl -s "https://livuma.com/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
