#!/bin/bash

source .venv/bin/activate

# Check if the Qdrant container is already running
if ! docker ps --filter "ancestor=qdrant/qdrant" --format "{{.ID}}" | grep -q .; then
    echo "Starting Qdrant container..."
    fuser -k 6333/tcp
    fuser -k 6334/tcp
    docker rm -f qdrant-dev 2>/dev/null || true
    docker run  --name qdrant-dev -d -p 6333:6333 -p 6334:6334 -v $CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z qdrant/qdrant
else
    echo "Qdrant container is already running."
fi

sleep 10
export UV_HTTP_TIMEOUT=1200

# Check if "No collections" is returned by mcp_pack list_db
existing_collections=$(uv run python -m mcp_pack.list_db)
if echo "$existing_collections" | grep -q "No collections found"; then
    echo "Creating databases..."
    uv run python -m mcp_pack.create_db https://github.com/starsimhub/starsim --verbose --include-notebooks --include-rst
    uv run python -m mcp_pack.create_db https://github.com/sciris/sciris --verbose --include-notebooks --include-rst
else
    echo "Collections already exist. Skipping database creation."
fi
echo $existing_collections
    	

if lsof -i:8001 | grep -q LISTEN; then
    echo "Sciris mcp is already running on 8001."
else
    echo "Starting sciris tool on port 8001..."
    pushd /workspace/src/mcp_pack
    nohup uv run python server.py --module_name=sciris --port=8001 --transport=sse > sciris.log 2>&1 &
    popd
fi

if lsof -i:8002 | grep -q LISTEN; then
    echo "Starsim mcp is already running on 8002."
else
    echo "Starting starsim tool on port 8002..."
    pushd /workspace/src/mcp_pack
    nohup uv run python server.py --module_name=starsim --port=8002 --transport=sse > starsim.log 2>&1 &
    popd
fi