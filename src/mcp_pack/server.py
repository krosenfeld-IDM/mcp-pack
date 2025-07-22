from pydantic import AnyHttpUrl
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient, models
from qdrant_client.models import Record
from sentence_transformers import SentenceTransformer
from typing import Any, Dict, List, Optional
import os
import argparse
import importlib
import httpx
import datetime
from .db_utils import string_to_uuid

search_docstring_desc_template = """
            Retrieves relevant docstrings from {module_name} module functions or classes based on a search query.
            
            This tool performs a semantic search against indexed {module_name} documentation to find
            the most relevant function or class docstrings that match the provided query.
            
            Args:
                query (str): A search query describing the {module_name} functionality you're looking for.
                    Examples: "How to use basic functions", "Core classes", "Data processing"
                limit (int, optional): Maximum number of relevant docstrings to return. Defaults to 3.
            
            Returns:
                List[str]: A list of formatted docstrings, each containing:
                    - The name and type (function/class) of the {module_name} object
                    - The complete docstring with parameter descriptions and usage notes
    """

search_docstring_fn_template = """search_{module_name}_docstring"""

get_source_code_desc_template = """
            Retrieves the source code for a specific function or class from the {module_name} module.
            
            This tool searches for the exact function or class name and returns its source code.
            
            Args:
                name (str): The exact name of the function or class you want to retrieve source code for.
                    Examples: "MyClass", "my_function", "process_data"
            
            Returns:
                str: The source code of the specified function or class, or an error message if not found.
    """

get_source_code_fn_template = """get_{module_name}_source_code"""

get_docstring_desc_template = """
            Retrieves the docstring for a specific function or class from the {module_name} module.
            
            This tool searches for the exact function or class name and returns its docstring.
            
            Args:
                name (str): The exact name of the function or class you want to retrieve the docstring for.
                    Examples: "MyClass", "my_function", "process_data"
            
            Returns:
                str: The docstring of the specified function or class, or an error message if not found.
    """

get_docstring_fn_template = """get_{module_name}_docstring"""

search_docs_desc_template = """
            Given a topic or query, searches documentation of {module_name} for relevant information like example and usage.
            
            Args:
                topic (str): Description of the task or topic you want to learn more about with {module_name}.
                    Examples: "Common use cases", "Working with main features", "Typical workflows"
            
            Returns:
                Dict[str, Any]: A dictionary containing:
                    - 'name': The name of the doc file or example
                    - 'result': The complete doc related to the search query
            
            Note:
                The returned examples may need adaptation for your specific use case.
            """

search_doc_fn_template = """search_{module_name}_docs"""

get_module_docstring_template = """
            Returns the docstring of a given Python function or class from a specified module.
            
            Args:
                module_name (str): The name of the Python module.
                obj_name (str): The name of the function or class within the module.
            
            Returns:
                str: The docstring of the object, or None if no docstring is present.
            
            Example:
                >>> get_docstring("math", "sqrt")
                'Return the square root of x.'
            """

get_module_docstring_fn_template = """get_{module_name}_docstring"""

get_module_functions_template = """
            Returns a list of all function names in the {module_name} module.            
            
            Returns:
                list: A list of function names in the module, or an error message if the module cannot be imported.
            
            Example:
                >>> get_functions("math")
                ['acos', 'acosh', 'asin', ...]
            """

get_module_functions_fn_template = """get_{module_name}_functions"""

class SimpleTokenVerifier(TokenVerifier):
    """Simple token verifier for demonstration."""

    async def verify_token(self, token: str) -> AccessToken | None:
            # Validate GitHub OAuth token by calling the user API
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.github.com/user", headers=headers)
                if resp.status_code == 200:
                    user = resp.json()
                    # Return a simple AccessToken object
                    auth_token = AccessToken(
                        sub=user.get("login", "github_user"),
                        token=token,
                        client_id="Ov23liJTVfc1OhRoZ35G",
                        scopes=["user"],
                        claims=user,
                    )
                    return auth_token
                else:
                    print(f"Auth failed: status={resp.status_code}, response={resp.text}")
                return None

class ModuleQueryServer:
    """
    A configurable server for providing AI agents with module documentation and examples.
    
    This server provides semantic search capabilities over module documentation, source code,
    and usage examples to help AI agents access relevant information and reduce hallucinations.
    """
    
    def __init__(
        self, 
        module_name: str,
        qdrant_url: str = "http://localhost:6333",
        encoder_model: str = "all-MiniLM-L6-v2",
        collection_name: Optional[str] = None,
        transport: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Initialize the ModuleQueryServer for a specific Python module.
        
        Args:
            module_name: Name of the Python module this server provides information about
            qdrant_url: URL for the Qdrant vector database
            encoder_model: SentenceTransformer model to use for encoding queries
            collection_name: Name of the Qdrant collection (defaults to module_name)
        """
        self.module_name = module_name
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name or module_name
        self.transport = transport if transport =="stdio" else "streamable-http"
        self.port = port
        
        # Initialize MCP server
        if self.transport == "streamable-http":
            self.mcp = FastMCP(f'{self.module_name}_pack',
                               # Use token verifier for authentication
                               token_verifier = SimpleTokenVerifier(),
                               auth = AuthSettings(
                                   issuer_url=AnyHttpUrl("https://api.github.com/user"),  # Authorization Server URL
                                   resource_server_url=AnyHttpUrl(f"http://localhost:{self.port}"),  # This server's URL
                                   required_scopes=["user"],
                               )
            )
        else:
            self.mcp = FastMCP(f'{self.module_name}_pack')

        # Initialize encoder
        self.encoder = SentenceTransformer(encoder_model)
        
    def get_qdrant_client(self):
        """Create and return a Qdrant client with the configured URL."""
        return QdrantClient(url=self.qdrant_url)
    
    def register_tools(self):
        """Register all query tools with the MCP server."""

        @self.mcp.tool(name=f"get_{self.module_name}_summary".format(module_name=self.module_name),
                       description=f"Get a high level summary of the {self.module_name} module.")
        async def get_module_summary() -> str:

            client = self.get_qdrant_client()
        
            result: list[Record] = client.retrieve(
                collection_name=self.collection_name,
                ids=[string_to_uuid("readme")]  
            )

            return result[0].payload["readme_content"]


        @self.mcp.tool(name = search_docstring_fn_template.format(module_name=self.module_name), 
                    description = search_docstring_desc_template.format(module_name = self.module_name))
        async def search_module_docstring(query: str, limit: int = 3) -> List[str]:

            client = self.get_qdrant_client()
            
            hits = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(query).tolist(),
                with_payload=True,
                limit=limit
            ).points
            
            result = []
            for i, hit in enumerate(hits):
                if i > 0:
                    result.append("#################################################")
                msg = (f'RESULT NUMBER: {i+1}:\n'
                       f'NAME: {hit.payload["name"]}\n' # type: ignore
                       f'TYPE: {hit.payload["type"]}\n' # type: ignore
                       f'DOCSTRING:\n {hit.payload["docstring"]}\n') # type: ignore
                result.append(msg)
                
            return result
        
        @self.mcp.tool(name = get_source_code_fn_template.format(module_name = self.module_name), 
                       description = get_source_code_desc_template.format(module_name = self.module_name))
        async def get_module_source_code(name: str) -> str:
            client = self.get_qdrant_client()
            
            # Search for exact match by name
            hits = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(name).tolist(),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="name",
                            match=models.MatchValue(value=name)
                        )
                    ]
                ),
                with_payload=True,
                limit=1
            ).points
            
            if not hits:
                return f"No function or class named '{name}' found in {self.module_name} module."
            
            hit = hits[0]
            return (f'NAME: {hit.payload["name"]}\n'
                    f'TYPE: {hit.payload["type"]}\n'
                    f'SOURCE CODE:\n{hit.payload["source_code"]}')
        
        @self.mcp.tool(name = get_docstring_fn_template.format(module_name = self.module_name), 
                       description = get_docstring_desc_template.format(module_name = self.module_name))
        async def get_module_docstring(name: str) -> str:
            client = self.get_qdrant_client()
            
            # Search for exact match by name
            hits = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(name).tolist(),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="name",
                            match=models.MatchValue(value=name)
                        )
                    ]
                ),
                with_payload=True,
                limit=1
            ).points
            
            if not hits:
                return f"No function or class named '{name}' found in {self.module_name} module."
            
            hit = hits[0]
            return (f'NAME: {hit.payload["name"]}\n'
                    f'TYPE: {hit.payload["type"]}\n'
                    f'DOCSTRING:\n{hit.payload["docstring"]}')
        
        @self.mcp.tool(name = search_doc_fn_template.format(module_name = self.module_name), 
                       description = search_docs_desc_template.format(module_name = self.module_name))
        async def search_module_docs(topic: str) -> Dict[str, Any]:
            client = self.get_qdrant_client()
            
            notebooks = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(topic).tolist(),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="doc")
                        )
                    ]
                ),
                with_payload=True,
                limit=1
            ).points
            
            if not notebooks:
                return {
                    'name': 'No examples found',
                    'type': 'none',
                    'result': f'No usage examples related to "{topic}" in {self.module_name}'
                }
            
            result = {
                'name': notebooks[0].payload['name'],  # type: ignore
                'type': notebooks[0].payload['type'],  # type: ignore
                'result': notebooks[0].payload['source_code'] # type: ignore
            }
            
            return result

        @self.mcp.tool(name = get_module_docstring_fn_template.format(module_name = self.module_name),
                       description = get_module_docstring_template.format(module_name = self.module_name))
        async def get_module_docstring(obj_name:str) -> str:
            try:
                module = importlib.import_module(self.module_name)
                obj = getattr(module, obj_name)
                return obj.__doc__
            except (ModuleNotFoundError, AttributeError) as e:
                return f"Error: {e}"

        @self.mcp.tool(name = get_module_functions_fn_template.format(module_name = self.module_name),
                       description = get_module_functions_template.format(module_name = self.module_name))
        async def get_module_functions() -> list:
            try:
                module = importlib.import_module(self.module_name)
                functions: list[str] = [name for name, obj in vars(module).items() if callable(obj)]
                return functions
            except ModuleNotFoundError as e:
                return [f"Error: {e}"]
                    
    def run(self):
        """Start the MCP server with the specified transport."""
        if self.transport == "streamable-http":
            self.mcp.settings.port = self.port
            self.mcp.settings.host = "0.0.0.0"
        self.mcp.run(transport=self.transport) # type: ignore

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ModuleQueryServer with a specified transport and module name.")
    parser.add_argument("--module_name", type=str, default=os.environ.get("MODULE_NAME", "sciris"), help="Name of the module to query.")
    parser.add_argument("--transport", type=str, default="stdio", help="Transport method for the MCP server (e.g., stdio, http, etc.)")
    parser.add_argument("--port", type=int, default=8000, help="Port number for the MCP server.")
    args = parser.parse_args()
   
    # Create and start the server with the specified port
    server = ModuleQueryServer(module_name=args.module_name, transport=args.transport, port=args.port)
    server.register_tools()

    # Pass the transport and port arguments to the run method
    server.run()