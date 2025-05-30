import argparse
import sys
import os
from dotenv import load_dotenv
from .create_db import GitModuleHelpDB
from .clean_db import QdrantCleaner
from .list_db import QdrantLister
from .server import ModuleQueryServer
from .version import __version__

def create_db_command(args):
    """Execute the create_db command."""
    # Get GitHub token from environment or args
    env_github_token = os.environ.get('GITHUB_TOKEN')
    github_token = args.github_token or env_github_token
    if not github_token:
        print("Warning: No GitHub token provided or found in environment. Authentication may be limited.")

    # Get OpenAI API key
    openai_api_key = args.openai_api_key or os.environ.get('OPENAI_API_KEY')

    # Process repository
    db = GitModuleHelpDB(
        db_path=args.db_path,
        qdrant_url=args.qdrant_url,
        github_token=github_token,
        openai_api_key=openai_api_key
    )
    
    # Fix repository URL format if it starts with @
    repo_url = args.repo_url
    if repo_url.startswith('@'):
        repo_url = repo_url[1:]
    
    db.process_repository(
        repo_url,
        module_name=args.module_name,
        output_dir=args.output_dir,
        verbose=args.verbose,
        include_notebooks=args.include_notebooks,
        include_rst=args.include_rst,
        exclude_tests=args.exclude_tests
    )

def clean_db_command(args):
    """Execute the clean_db command."""
    cleaner = QdrantCleaner(qdrant_url=args.qdrant_url)
    
    if args.collection:
        if cleaner.delete_collection(args.collection):
            print(f"Successfully deleted collection: {args.collection}")
        else:
            print(f"Failed to delete collection: {args.collection}")
    else:
        deleted = cleaner.delete_all_collections()
        if deleted:
            print("Successfully deleted the following collections:")
            for collection in deleted:
                print(f"- {collection}")
        else:
            print("No collections were deleted (database may be empty)")

def list_db_command(args):
    """Execute the list_db command."""
    lister = QdrantLister(qdrant_url=args.qdrant_url)
    collections = lister.list_collections()

    if collections:
        print("Collections in Qdrant:")
        for collection in collections:
            print(f"- {collection}")
    else:
        print("No collections found in Qdrant.")

def create_server_command(args):
    """Execute the create_server command."""
    server = ModuleQueryServer(
        module_name=args.module_name,
        qdrant_url=args.qdrant_url,
        encoder_model=args.encoder_model,
        collection_name=args.collection_name
    )
    server.register_tools()
    server.run(transport=args.transport, port=args.port)

def main():
    """Main CLI entry point."""

    dotenv_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()
    
    parser = argparse.ArgumentParser(description=f'MCP Pack v{__version__} - Tools for creating and managing documentation databases')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Version command
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    # Create DB command
    create_parser = subparsers.add_parser('create_db', help='Create documentation database for a GitHub repository')
    create_parser.add_argument('repo_url', help='GitHub repository URL (can be prefixed with @)')
    create_parser.add_argument('--output-dir', '-o', help='Directory to save JSONL output', default=None)
    create_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    create_parser.add_argument('--include-notebooks', action='store_true', help='Include Jupyter notebooks')
    create_parser.add_argument('--include-rst', action='store_true', help='Include RST files')
    create_parser.add_argument('--exclude-tests', action='store_true', help='Exclude test files and directories')
    create_parser.add_argument('--module-name', help='Name of the module (defaults to repository name)')
    create_parser.add_argument('--db-path', help='Path to store the database', default=None)
    create_parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    create_parser.add_argument('--github-token', help='GitHub personal access token', default=None)
    create_parser.add_argument('--openai-api-key', help='OpenAI API key', default=None)
    
    # Clean DB command
    clean_parser = subparsers.add_parser('clean_db', help='Clean Qdrant database collections')
    clean_parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    clean_parser.add_argument('--collection', help='Specific collection to delete (optional, if not provided, all collections will be deleted)')
    
    # List DB command
    list_parser = subparsers.add_parser('list_db', help='List all collections in the Qdrant database')
    list_parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    
    # Create Server command
    server_parser = subparsers.add_parser('create_server', help='Create and run a ModuleQueryServer')
    server_parser.add_argument('--module-name', help='Name of the module to query', required=True)
    server_parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    server_parser.add_argument('--encoder-model', help='SentenceTransformer model to use', default='all-MiniLM-L6-v2')
    server_parser.add_argument('--collection-name', help='Name of the Qdrant collection (defaults to module_name)')
    server_parser.add_argument('--transport', help='Transport method for the MCP server', default='stdio', choices=['stdio', 'sse'])
    server_parser.add_argument('--port', type=int, help='Port number for the MCP server', default=8000)
    
    args = parser.parse_args()
    
    if args.command == 'create_db':
        create_db_command(args)
    elif args.command == 'clean_db':
        clean_db_command(args)
    elif args.command == 'list_db':
        list_db_command(args)
    elif args.command == 'create_server':
        create_server_command(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()