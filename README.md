# mcp-pack
Repository for accessing package artifacts via MCP

## Setup
Install [uv](https://github.com/astral-sh/uv) and run:

```bash
uv venv
source .venv/bin/activate
uv pip install .
```

add to a `.env` file a Github personal access token with read access and OpenAI API key (required for processing notebooks):

```
GITHUB_TOKEN=github_pat_1234567890
OPENAI_API_KEY=sk-1234567890
```

## Knowledge base
`mcp-pack` uses a vector database for semantic search of docstrings.

### Creating the knowledge base
Navigate to one of the directories in `examples/` and start the qdrant server:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_db:/qdrant/storage:z" \
    qdrant/qdrant
```
and then generate the database, specifying the repository:
```bash
python -m mcp_pack.create_db https://github.com/user/repo
```

### Cleaning the database
To clean up the Qdrant database, you can use the clean_db script. This will delete either all collections or a specific collection:

```bash
# Delete all collections
python -m mcp_pack.clean_db

# Delete a specific collection
python -m mcp_pack.clean_db --collection collection_name

# Use a different Qdrant server URL
python -m mcp_pack.clean_db --qdrant-url http://custom-url:6333
```

## Using the server

Once you have a database created and the `qdrant` docker running, you can add the server to you `mcp.json` (or similar) file. See the `examples/` for more details. Below is more information for code editors:
- [VSCode](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- [cursor](https://docs.cursor.com/context/model-context-protocol) (NB: may not work properly with remote connections)
- [windsurf](https://docs.windsurf.com/windsurf/mcp)

Note that due to `qdrant`, it can take some time to initialize the server for the first time. Make sure that you use
absolute filepaths in the `mcp.json`. You may also need to set an absolute path for `uv`.

## Requirements
- Docker
- uv


## Additional info

```bash
> python -m mcp_pack.create_db --help 
Create documentation database for a GitHub repository

positional arguments:
  repo_url              GitHub repository URL

options:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR, -o OUTPUT_DIR
                        Directory to save JSONL output
  --verbose, -v         Verbose output
  --include-notebooks   Include Jupyter notebooks
  --include-rst         Include rst files
  --db-path DB_PATH     Path to store the database
  --qdrant-url QDRANT_URL
                        Qdrant server URL
  --github-token GITHUB_TOKEN
                        GitHub personal access token
  --openai-api-key OPENAI_API_KEY
                        OpenAI API key
```