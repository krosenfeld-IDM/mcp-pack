#!/bin/bash

docker run -d -p 6333:6333 -p 6334:6334 -v $CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z qdrant/qdrant
export UV_HTTP_TIMEOUT=120
cd src/mcp_langchain_agent
uv run python -m streamlit run app.py