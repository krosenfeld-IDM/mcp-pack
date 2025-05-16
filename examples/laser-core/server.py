
#!/usr/bin/env python3
"""
MCP Server for providing pandas module information to AI agents.

This script sets up a server that can answer queries about pandas documentation,
source code, and usage examples through semantic search.

Add to mcp.json (updating with correct absolute paths)
```
    "laser_helper": {
        "command": "${HOME}/.local/bin/uv",
        "args": [
            "--directory",
            "${HOME}/projects/mcp-pack/examples/laser-core/server.py",
            "run",
            "server.py"
        ]
    } 
```

"""

import os
from mcp_pack.server import ModuleQueryServer

# Create server instance for sciris
laser_server = ModuleQueryServer(
    module_name="laser",
    server_name="laser_helper",
    qdrant_url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
    collection_name="laser"
)

# Register all tools with the server
laser_server.register_tools()

# Run the server
if __name__ == "__main__":
    print(f"Starting laser documentation server...")
    laser_server.run(transport="stdio")