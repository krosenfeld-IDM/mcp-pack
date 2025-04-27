
#!/usr/bin/env python3
"""
MCP Server for providing pandas module information to AI agents.

This script sets up a server that can answer queries about pandas documentation,
source code, and usage examples through semantic search.

Add to mcp.json (updating with correct absolute paths)
```
    "sciris_helper": {
        "command": "${HOME}/.local/bin/uv",
        "args": [
            "--directory",
            "${HOME}/projects/mcp-pack/examples/sciris/server.py",
            "run",
            "server.py"
        ]
    } 
```

"""

import os
from mcp_pack.server import ModuleQueryServer

# Create server instance for sciris
sciris_server = ModuleQueryServer(
    module_name="sciris",
    server_name="sciris_helper",
    qdrant_url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
    collection_name="sciris"
)

# Register all tools with the server
sciris_server.register_tools()

# Run the server
if __name__ == "__main__":
    print(f"Starting sciris documentation server...")
    sciris_server.run(transport="stdio")