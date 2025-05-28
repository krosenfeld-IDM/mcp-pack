# README

```bash
python -m mcp_pack.create_db https://github.com/sciris/sciris --include-notebooks --include-rst --verbose --exclude-tests
```

and add to `mcp.json` (or equivalent) after correcting the full path:

```json
    "sciris_helper": {
        "command": "uv",
        "args": [
            "--directory",
            "PATHTO/mcp-pack/examples/sciris",
            "run",
            "server.py"
        ]
    }      
```