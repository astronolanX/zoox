#!/bin/bash
cd /Users/nolan/Desktop/reef
exec uv run python -W ignore -m reef.mcp.server "$@"
