from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from typing import Any, Dict, List, Optional
import os
import argparse

get_docstring_template = """
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

get_source_code_template = """
            Retrieves relevant source code implementations from {module_name} module based on a search query.
            
            This tool performs a semantic search against indexed {module_name} source code to find
            the most relevant function or class implementations that match the provided query.
            Use this when you need to understand how specific {module_name} functionality is implemented.
            
            Args:
                query (str): A search query describing the {module_name} functionality you're looking for.
                    Examples: "Implementation details of", "How specific feature works", "Core logic"
                limit (int, optional): Maximum number of relevant source code snippets to return. Defaults to 3.
            
            Returns:
                List[str]: A list of formatted source code snippets, each containing:
                    - The name and type (function/class) of the {module_name} object
                    - The complete source code implementation
            """

get_usage_example_template = """
            Finds the most relevant code example for accomplishing a specific task with {module_name}.
            
            This tool searches through a collection of notebook examples to find a relevant
            code sample that demonstrates how to accomplish a specific task using {module_name}.
            Use this tool when you need practical examples rather than just documentation.
            
            Args:
                task (str): Description of the task you want to accomplish with {module_name}.
                    Examples: "Common use cases", "Working with main features", "Typical workflows"
                include_context (bool, optional): Whether to include surrounding context such as 
                    imports, setup code, and additional explanations. Setting to False returns
                    only the core implementation. Defaults to True.
            
            Returns:
                Dict[str, Any]: A dictionary containing:
                    - 'name': The name of the notebook or example
                    - 'type': The type of the resource (usually "notebook")
                    - 'result': The complete code example with explanations
            
            Note:
                The returned examples are from real usage scenarios and may need adaptation
                for your specific use case.
            """
class ModuleQueryServer:
    """
    A configurable server for providing AI agents with module documentation and examples.
    
    This server provides semantic search capabilities over module documentation, source code,
    and usage examples to help AI agents access relevant information and reduce hallucinations.
    """
    
    def __init__(
        self, 
        module_name: str,
        server_name: Optional[str] = None,
        qdrant_url: str = "http://localhost:6333",
        encoder_model: str = "all-MiniLM-L6-v2",
        collection_name: Optional[str] = None
    ):
        """
        Initialize the ModuleQueryServer for a specific Python module.
        
        Args:
            module_name: Name of the Python module this server provides information about
            server_name: Name for the MCP server instance (defaults to f"{module_name}_helper")
            qdrant_url: URL for the Qdrant vector database
            encoder_model: SentenceTransformer model to use for encoding queries
            collection_name: Name of the Qdrant collection (defaults to module_name)
        """
        self.module_name = module_name
        self.server_name = server_name or f"{module_name}_helper"
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name or module_name
        
        # Initialize MCP server
        self.mcp = FastMCP(self.server_name)
        
        # Initialize encoder
        self.encoder = SentenceTransformer(encoder_model)
        
    def get_qdrant_client(self):
        """Create and return a Qdrant client with the configured URL."""
        return QdrantClient(url=self.qdrant_url)
    
    def register_tools(self):
        """Register all query tools with the MCP server."""
        
        @self.mcp.tool(description = get_docstring_template.format(module_name = self.module_name))
        async def get_docstring(query: str, limit: int = 3) -> List[str]:

            client = self.get_qdrant_client()
            
            hits = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(query).tolist(),
                with_payload=True,
                limit=limit
            ).points
            
            result = []
            for hit in hits:
                msg = f"####{hit.payload['name']} ({hit.payload['type']})####\n{hit.payload['docstring']}\n"
                result.append(msg)
                
            return result
        
        @self.mcp.tool(description = get_source_code_template.format(module_name = self.module_name))
        async def get_source_code(query: str, limit: int = 3) -> List[str]:

            client = self.get_qdrant_client()
            
            search_result = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(query).tolist(),
                with_payload=True,
                limit=limit
            ).points
            
            result = []
            for point in search_result:
                msg = f"####{point.payload['name']} ({point.payload['type']})####\n{point.payload['source_code']}\n"
                result.append(msg)
                
            return result
        
        @self.mcp.tool(description = get_usage_example_template.format(module_name = self.module_name))
        async def get_usage_example(task: str, include_context: bool = True) -> Dict[str, Any]:
            client = self.get_qdrant_client()
            
            notebooks = client.query_points(
                collection_name=self.collection_name,
                query=self.encoder.encode(task).tolist(),
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="notebook")
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
                    'result': f'No usage examples found for "{task}" in {self.module_name}'
                }
            
            result = {
                'name': notebooks[0].payload['name'], 
                'type': notebooks[0].payload['type'], 
                'result': notebooks[0].payload['source_code']
            }
            
            return result
    
    def run(self, transport: str = "stdio", port: int = 8000):
        """Start the MCP server with the specified transport."""
        if transport == "sse":
            self.mcp.settings.port = port
        self.mcp.run(transport=transport)

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ModuleQueryServer with a specified transport and module name.")
    parser.add_argument("--module_name", type=str, default=os.environ.get("MODULE_NAME", "sciris"), help="Name of the module to query.")
    parser.add_argument("--transport", type=str, default="stdio", help="Transport method for the MCP server (e.g., stdio, http, etc.)")
    parser.add_argument("--port", type=int, default=8000, help="Port number for the MCP server.")
    args = parser.parse_args()
   
    # Create and start the server with the specified port
    server = ModuleQueryServer(args.module_name)
    server.register_tools()

    # Pass the transport and port arguments to the run method
    server.run(transport=args.transport, port=args.port)