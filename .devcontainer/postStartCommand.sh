#!/bin/bash

# Check if the Qdrant container is already running
if ! docker ps --filter "ancestor=qdrant/qdrant" --format "{{.ID}}" | grep -q .; then
    echo "Starting Qdrant container..."
    docker run -d -p 6333:6333 -p 6334:6334 -v $CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z qdrant/qdrant
else
    echo "Qdrant container is already running."
fi

sleep 10
export UV_HTTP_TIMEOUT=120

# Check if "No collections" is returned by mcp_pack list_db
existing_collections=$(mcp_pack list_db)
if echo "$existing_collections" | grep -q "No collections found"; then
    echo "Creating databases..."
    mcp_pack create_db https://github.com/starsimhub/starsim --verbose --include-notebooks --include-rst
    mcp_pack create_db https://github.com/sciris/sciris --verbose --include-notebooks --include-rst
else
    echo "Collections already exist. Skipping database creation."
fi
echo $existing_collections
    	

# Start streamlit ob port 8501
if lsof -i:8501 | grep -q LISTEN; then
    echo "Streamlit app is already running on port 8501."
else
    echo "Starting Streamlit app on port 8501..."
    cd src/mcp_langchain_agent
    uv run python -m streamlit run app.py --server.port=8501
fi