#!/bin/bash

# Check if the Qdrant container is already running
if ! docker ps --filter "ancestor=qdrant/qdrant" --format "{{.ID}}" | grep -q .; then
    echo "Starting Qdrant container..."
    fuser -k 6333/tcp
    fuser -k 6334/tcp
    docker run -d -p 6333:6333 -p 6334:6334 -v $CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z qdrant/qdrant
else
    echo "Qdrant container is already running."
fi

sleep 10
export UV_HTTP_TIMEOUT=1200

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
    	

if lsof -i:8001 | grep -q LISTEN; then
    echo "Sciris mcp is already running on 8001."
else
    echo "Starting sciris tool on port 8001..."
    cd src/mcp_pack
    uv run python server.py --module_name=sciris --port=8001 --transport=sse > /dev/null 2>&1 &
fi

if lsof -i:8002 | grep -q LISTEN; then
    echo "Starsim mcp is already running on 8002."
else
    echo "Starting starsim tool on port 8002..."
    cd src/mcp_pack
    uv run python server.py --module_name=starsim --port=8002 --transport=sse > /dev/null 2>&1 &
fi

# Start mcp client FAST API at port 8081
if lsof -i:8081 | grep -q LISTEN; then
    echo "mcp client FAST API is already running on port 8081."
else
    echo "Starting mcp client FAST API on port 8081..."
    cd ../../src/mcp_langchain_agent
    uvicorn app01:app --reload --port 8081 > /dev/null 2>&1 &
fi

# Start streamlit langgraph at port 8502
if lsof -i:8502 | grep -q LISTEN; then
    echo "streamlit langgraph is already running on port 8502."
else
    echo "Starting UI on port 8502..."
    uv run python -m streamlit run ui01.py --server.port=8502  > /dev/null 2>&1 &
fi

# simple client
# Start streamlit server at port 8501
if lsof -i:8501 | grep -q LISTEN; then
    echo "Streamlit app is already running on port 8501."
else
    echo "Starting Streamlit app on port 8501..."
    uv run python -m streamlit run app.py --server.port=8501
fi