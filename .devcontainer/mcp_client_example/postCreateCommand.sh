#!/bin/bash
export UV_HTTP_TIMEOUT=6000
pip install uv
# pip install -e .
uv sync
uv pip compile --group mcp_client 
