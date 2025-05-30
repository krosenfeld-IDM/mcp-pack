from mcp_pack.create_db import GitModuleHelpDB
from dotenv import load_dotenv
import os

load_dotenv()

print("Setting up Sciris database...")
module: GitModuleHelpDB = GitModuleHelpDB(
    qdrant_url="http://localhost:6333",
    github_token=os.getenv("GITHUB_TOKEN"),
)
print("Processing Sciris repository...")
module.process_repository(
    "hhttps://github.com/sciris/sciris",
    module_name="sciris",
    exclude_tests=True,
    include_notebooks=True,
    include_rst=False,
)