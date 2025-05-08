#!/bin/bash

# Start mcp client FAST API at port 8081
if lsof -i:8081 | grep -q LISTEN; then
    echo "mcp client FAST API is already running on port 8081."
else
    echo "Starting mcp client FAST API on port 8081..."
    pushd /workspace/examples/mcp_langchain_agent
    uv run uvicorn app:app --reload  --host 0.0.0.0 --port 8081 > mcp_app.log 2>&1 &
    popd
fi

# Start streamlit langgraph at port 8501
if lsof -i:8501 | grep -q LISTEN; then
    echo "streamlit UI is already running on port 8501."
else
    echo "Starting UI on port 8502..."
    pushd examples/mcp_langchain_agent
    uv run python -m streamlit run ui.py --server.port=8501  > mcp_ui.log 2>&1 &
    popd
fi
