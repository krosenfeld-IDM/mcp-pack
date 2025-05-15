#!/bin/bash
export UV_HTTP_TIMEOUT=6000
pip install uv
# pip install -e .
uv venv
uv pip install --group dev
uv pip install --group mcp_client