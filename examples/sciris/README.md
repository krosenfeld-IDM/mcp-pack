# README

Start the qdrant server:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_db:/qdrant/storage:z" \
    qdrant/qdrant
```

and create the database

```bash
python -m mcp_pack.create_db https://github.com/sciris/sciris --include-notebooks --verbose
```

and add to `mcp.json` (or equivalent) after correcting the full path:

```json
    "sciris_helper": {
        "command": "uv",
        "args": [
            "--directory",
            "/home/USER/mcp-pack/examples/sciris",
            "run",
            "server.py"
        ]
    }      
```