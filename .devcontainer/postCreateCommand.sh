#!/bin/bash

docker run -d -p 6333:6333 -p 6334:6334 -v "$CODESPACE_VSCODE_FOLDER/qdrant_db:/qdrant/storage:z" qdrant/qdrant
pip install uv
pip install -e .
mcp_pack create_db https://github.com/starsimhub/starsim --verbose --include-notebooks --include-rst
mcp_pack create_db https://github.com/sciris/sciris --verbose --include-notebooks --include-rst
mcp_pack list_db
    