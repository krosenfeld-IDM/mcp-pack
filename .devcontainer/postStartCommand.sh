#!/bin/bash

docker run -d -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_db:/qdrant/storage:z qdrant/qdrant
cd src/mcp_langchain_agent
uv run python -m streamlit run app.py