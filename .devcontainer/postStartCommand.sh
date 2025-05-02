#!/bin/bash

docker run -d -p 6333:6333 -p 6334:6334 -v $CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z qdrant/qdrant
sleep 30
export UV_HTTP_TIMEOUT=120

mcp_pack create_db https://github.com/starsimhub/starsim --verbose --include-notebooks --include-rst
mcp_pack create_db https://github.com/sciris/sciris --verbose --include-notebooks --include-rst
mcp_pack list_db
    
	
cd src/mcp_langchain_agent
uv run python -m streamlit run app.py