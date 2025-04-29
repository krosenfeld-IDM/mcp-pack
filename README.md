# MCP Pack

A tool for creating and managing documentation databases from GitHub repositories.

## Quickstart to create a database
With a Qdrant server running:
```bash
uvx mcp_pack create_db https://github.com/user/repo
```

see the `examples/` folder for how to setup the MCP server.

## Installation

```bash
# Install from pip
pip install mcp_pack
```

## Prerequisites

- **Qdrant server running** (by default at http://localhost:6333)
- GitHub token (optional, but recommended to avoid rate limits)
- OpenAI API key (optional, for summarizing Jupyter notebooks)

## Usage
See `example/` folder.

### Create a documentation database

```bash
# Basic usage
mcp_pack create_db https://github.com/user/repo

# With @ prefix syntax
mcp_pack create_db @https://github.com/user/repo

# With additional options
mcp_pack create_db @https://github.com/user/repo \
    --output-dir ./output \
    --verbose \
    --include-notebooks \
    --include-rst \
    --github-token YOUR_GITHUB_TOKEN \
    --openai-api_key YOUR_OPENAI_API_KEY
```

### Clean the database

```bash
# Delete all collections
mcp_pack clean_db

# Delete a specific collection
mcp_pack clean_db --collection repo-name
```

### List Database Collections

To list all collections in the Qdrant database, use the following command:

```bash
# Use default Qdrant
mcp_pack list_db

# Use Custom Qdrant server URL 
mcp_pack list_db --qdrant-url http://localhost:6333
```

This will display all the collections currently stored in the Qdrant database.

## Environment Variables

You can set environment variables instead of passing command-line arguments:

```bash
# Create a .env file
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
```

## Options

### create_db

- `repo_url`: GitHub repository URL (can be prefixed with @)
- `--output-dir`, `-o`: Directory to save JSONL output
- `--verbose`, `-v`: Verbose output
- `--include-notebooks`: Include Jupyter notebooks
- `--include-rst`: Include RST files
- `--db-path`: Path to store the database
- `--qdrant-url`: Qdrant server URL (default: http://localhost:6333)
- `--github-token`: GitHub personal access token
- `--openai-api-key`: OpenAI API key

### clean_db

- `--qdrant-url`: Qdrant server URL (default: http://localhost:6333)
- `--collection`: Specific collection to delete (optional)

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

``` bash
python -m mcp_pack.clean_db --help
Clean Qdrant database collections

options:
  -h, --help            show this help message and exit
  --qdrant-url QDRANT_URL
                        Qdrant server URL
  --collection COLLECTION
                        Specific collection to delete (optional, if not provided, all collections will be deleted)
```