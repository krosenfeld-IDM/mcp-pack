# mcp-pack
Repository for accessing package artifacts via MCP

To generate the database:
```bash
python -m mcp_pack.create_db
```

## Requirements
- Docker
- uv

## Setup
Install [uv](https://github.com/astral-sh/uv) and run:

```bash
uv venv
source .venv/bin/activate
uv pip install .
```

add to a `.env` file a GITHUB personal access token with read access:

```
GITHUB_TOKEN=github_pat_1234567890
```

then navigate to one of the `examples/' directories and follow instructions there.