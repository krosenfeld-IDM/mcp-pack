import ast
import os
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
import qdrant_client
from qdrant_client import models
from sentence_transformers import SentenceTransformer
import requests
import base64
from urllib.parse import urlparse
from dotenv import load_dotenv
import nbformat
from nbconvert import PythonExporter
import openai
import argparse

from .db_utils import string_to_uuid

def parse_repo_url(repo_url: str) -> Tuple[str, str]:
    """Parse a GitHub repository URL into owner and repo name."""
    parsed_url = urlparse(repo_url)  # noqa: F821
    path_parts = parsed_url.path.strip('/').split('/')
    owner, repo = path_parts[0], path_parts[1]
    return owner, repo


class GitModuleHelpDB:
    """A class for creating and managing a documentation database for Python modules from GitHub repositories.
    
    This class provides functionality to analyze Python packages from GitHub repositories, extract documentation,
    and create a searchable database using Qdrant for efficient documentation retrieval.
    """
    
    def __init__(self, db_path: str | None = None, qdrant_url: str = 'http://localhost:6333',
                 model: str | None = 'gpt-4o',
                 github_token: str | None = None, openai_api_key: str | None = None):
        """Initialize the GitModuleHelpDB instance.
        
        Args:
            db_path: Path to store the database (optional)
            qdrant_url: URL of the Qdrant server (default: 'http://localhost:6333')
            github_token: GitHub personal access token for API access (optional)
            docs_folder: Optional path to a folder containing .ipynb docs
            openai_api_key: API key for OpenAI (optional, required for summarization)
        """
        self.db_path = db_path
        self.qdrant_url = qdrant_url
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = qdrant_client.QdrantClient(qdrant_url)
        self.github_token = github_token
        self.headers = {'Authorization': f'Bearer {github_token}'} if github_token else {}
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.module_name: str | None = None
        self.model: str | None = model
        # Add file content cache to reduce API calls
        self.file_cache = {}
        self.dir_cache = {}
        # Maximum number of retries for API calls
        self.max_retries = 5
    
    def _extract_docstring(self, node: ast.AST) -> tuple[str, str]:
        """Extract docstring from an AST node and its header."""
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            return "", ""
        
        docstring = ast.get_docstring(node)
        if not docstring:
            return "", ""
        
        lines: list[str] = [line.strip() for line in docstring.split('\n')]
        header = next((line for line in lines if line), "")
        
        if len(lines) > 1 and not lines[1]:
            return docstring, header
        
        header_lines = []
        for line in lines:
            if not line or line.startswith(' '):
                break
            header_lines.append(line)
        
        return docstring, ' '.join(header_lines)
    
    def _get_source_code(self, node: ast.AST, source: str) -> str:
        """Get the source code for a node."""
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return ""
        
        start_lineno: int = node.lineno
        end_lineno: int | None = node.end_lineno if hasattr(node, 'end_lineno') else start_lineno
        lines = source.split('\n')
        return '\n'.join(lines[start_lineno-1:end_lineno])
    
    def _make_github_request(self, url: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """Make a GitHub API request with rate limit handling and exponential backoff.
        
        Args:
            url: The GitHub API URL to request
            retry_count: Current retry attempt (used internally for recursion)
            
        Returns:
            JSON response or None if all retries failed
        """
        try:
            response = requests.get(url, headers=self.headers)
            
            # Check for rate limit headers
            rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            
            # If we're close to the rate limit, wait until reset
            if rate_limit_remaining < 5 and rate_limit_reset > time.time():
                wait_time = rate_limit_reset - time.time() + 5  # Add 5 seconds buffer
                print(f"Rate limit almost reached. Waiting {wait_time:.1f} seconds until reset...")
                time.sleep(wait_time)
                return self._make_github_request(url, retry_count)
            
            # Handle rate limit exceeded
            if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                if retry_count >= self.max_retries:
                    print(f"Maximum retries ({self.max_retries}) reached. GitHub API rate limit exceeded.")
                    print("Consider using a GitHub token to increase your rate limit.")
                    return None
                
                # Calculate wait time with exponential backoff and jitter
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                print(f"Rate limit exceeded. Retrying in {wait_time:.1f} seconds (attempt {retry_count + 1}/{self.max_retries})...")
                time.sleep(wait_time)
                return self._make_github_request(url, retry_count + 1)
            
            # Handle other errors
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            if retry_count >= self.max_retries:
                print(f"Maximum retries ({self.max_retries}) reached. Last error: {str(e)}")
                return None
            
            # Calculate wait time with exponential backoff and jitter
            wait_time = (2 ** retry_count) + random.uniform(0, 1)
            print(f"Request error: {str(e)}. Retrying in {wait_time:.1f} seconds (attempt {retry_count + 1}/{self.max_retries})...")
            time.sleep(wait_time)
            return self._make_github_request(url, retry_count + 1)
    
    def _get_github_file_content(self, owner: str, repo: str, path: str) -> str:
        """Get the content of a file from a GitHub repository."""
        # Check cache first
        cache_key = f"{owner}/{repo}/{path}"
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]
        
        url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        response_json = self._make_github_request(url)
        
        if not response_json:
            raise ValueError(f"Failed to get content for {path}")
        
        content = response_json['content']
        decoded_content = base64.b64decode(content).decode('utf-8')
        
        # Cache the result
        self.file_cache[cache_key] = decoded_content
        
        return decoded_content
    
    def _get_github_files(self, owner: str, repo: str, path: str = '', load_ipynb: bool = False, load_rst: bool = False, exclude_tests: bool = False) -> Dict[str, List[Dict[str, Any]] | None]:
        """Get all Python, Jupyter Notebook (.ipynb), and RST (.rst) files from a GitHub repository when their flags are True.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository
            load_ipynb: Whether to include Jupyter notebooks
            load_rst: Whether to include RST files
            exclude_tests: Whether to exclude test files and directories
            
        Returns:
            Dictionary with keys:
            - 'py': List of Python files
            - 'ipynb': List of Jupyter notebook files (if load_ipynb is True)
            - 'rst': List of RST files (if load_rst is True)
            - 'readme': README file content (if exists)
        """
        # Check cache first
        cache_key: str = f"{owner}/{repo}/{path}"
        if cache_key in self.dir_cache:
            return self.dir_cache[cache_key]
        
        url: str = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        response_json: dict[str, Any] | None = self._make_github_request(url)
        
        if not response_json:
            raise ValueError(f"Failed to list contents for {path}")
        
        result: Dict[str, List[Dict[str, Any]] | None] = {
            'py': [],
            'ipynb': [],
            'rst': [],
            'readme': []
        }
        
        for item in response_json:
            # Skip test files and directories if exclude_tests is True
            if exclude_tests and (
                item['name'].startswith('test_') or 
                item['name'].endswith('_test.py') or 
                item['name'] == 'tests' or 
                item['name'] == 'conftest.py' or
                item['name'].endswith('_spec.py') or
                '_test_' in item['name'] or
                'test' in item['name'].lower() or
                any(test_dir in item['name'].lower() for test_dir in ['test_', '_test', 'testing', 'unit_tests', 'integration_tests'])
            ):
                continue
                
            if item['type'] == 'file' :
                if  item['name'].endswith('.py'):
                    result['py'].append(item)
                elif  item['name'].endswith('.ipynb') and load_ipynb:
                    result['ipynb'].append(item)
                elif  item['name'].endswith('.rst') and load_rst:
                    result['rst'].append(item)
                elif  item['name'].lower() in ['readme.md', 'readme.rst']:
                    result['readme'].append(item)
            elif item['type'] == 'dir':
                subdir_result = self._get_github_files(
                    owner, repo, item['path'], 
                    load_ipynb=load_ipynb, 
                    load_rst=load_rst,
                    exclude_tests=exclude_tests
                )
                result['py'].extend(subdir_result['py'])
                result['ipynb'].extend(subdir_result['ipynb'])
                result['rst'].extend(subdir_result['rst'])
            else:
                raise ValueError(f"Unexpected item type: {item['type']}")
                # if subdir_result['readme'] is not None:
                # result['readme'].extend(subdir_result['readme'])
        
        # Cache the result
        self.dir_cache[cache_key] = result
        
        return result
    
    def analyze_python_file(self, owner: str, repo: str, file_path: str) -> List[Dict[str, Any]]:
        """Analyze a Python file from GitHub and extract function and class information."""
        source = self._get_github_file_content(owner, repo, file_path)
        tree = ast.parse(source)
        results = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring, docstring_header = self._extract_docstring(node)
                result = {
                    'name': node.name,
                    'type': 'function' if isinstance(node, ast.FunctionDef) else 'class',
                    'docstring': docstring,
                    'docstring_header': docstring_header,
                    'source_code': self._get_source_code(node, source),
                    'file': file_path,
                    'repo': f'{owner}/{repo}'
                }
                results.append(result)
        
        return results
    
    def analyze_repository(self, repo_url: str, include_notebooks: bool = False, include_rst: bool = False, exclude_tests: bool = False) -> dict[str, Any]:
        """Analyze all .py, .ipynb, and .rst files in a GitHub repository when their flags are True.
        
        Args:
            repo_url: URL of the GitHub repository to analyze
            include_notebooks: Whether to include Jupyter notebooks
            include_rst: Whether to include RST files
            exclude_tests: Whether to exclude test files and directories
            
        Returns:
            List of analyzed documentation items
        """

        # Parse the repository URL
        owner, repo = parse_repo_url(repo_url)
        
        # Get all files
        files = self._get_github_files(
            owner, repo, 
            load_ipynb=include_notebooks, 
            load_rst=include_rst,
            exclude_tests=exclude_tests
        )
        all_results = []
        
        # Process Python files
        for file in files['py']:
            if file['name'] != '__init__.py':  # Skip __init__.py files
                try:
                    results = self.analyze_python_file(owner, repo, file['path'])
                    all_results.extend(results)
                    print(f"Processed {file['path']}")
                except Exception as e:
                    print(f"Error processing {file['path']}: {str(e)}")
        
        # Process notebooks
        if files['ipynb']:
            notebook_docs: list = self._process_notebooks(repo_url, files['ipynb'])
            all_results.extend(notebook_docs)

        # Process rst files
        if files['rst']:
            rst_docs: list[dict[str, Any]] = self._process_rst(repo_url, files['rst'])
            all_results.extend(rst_docs)

        # Process readme files
        if files['readme']:
            readme_docs: list[dict[str, Any]] = self._process_readme(repo_url, files['readme'])
        else:
            readme_docs = []

        return {'results': all_results, 'readme_docs': readme_docs}
    
    def _process_readme(self, repo_url: str, readme_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process README files in the repository."""

        # Parse the repository URL
        parsed_url = urlparse(repo_url)
        path_parts: list[str] = parsed_url.path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1]

        docs = []
        for readme in readme_files:
            if readme['name'].endswith('.md') or readme['name'].endswith('.rst'):
                try:
                    content = self._get_github_file_content(owner, repo, readme['path'])
                    doc = {
                        "name": readme['name'],
                        "type": "readme",
                        "file": readme['path'],
                        "repo": f"{owner}/{repo}",
                        "readme_content": content,
                    }
                    docs.append(doc)
                except Exception as e:
                    print(f"Error processing readme file {readme['name']}: {e}")
        return docs
    
    def _summarize_document(self, py_code: str, fname: str) -> str:
        """Summarize the notebook using OpenAI chat.completions."""
        if not self.openai_api_key:
            return "[OpenAI API key not provided, cannot summarize]"
        prompt = (
            f"Summarize the following document ({fname}) for the repository and associated package '{self.module_name}' in a concise paragraph. "
            f"### Document ### \n{py_code[:4000]}"
        )
        try:
            client = openai.Client()
            response = client.chat.completions.create(
                model= self.model,
                messages=[{"role": "system", "content": (f"You are a helpful assistant tasked to summarize a document."
                                                         f"Focus on the main functionality and what a user will learn about the repository and associated package: '{self.module_name}'."
                                                         f"Make sure to identify what functions, classes, and capabilities are featured in the document."
                                                        )},
                          {"role": "user", "content": prompt}],
                max_tokens=10_000,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[OpenAI error: {e}]"    
    
    def _process_notebooks(self, repo_url: str, notebooks: List[Dict[str, Any]]) -> list:
        """Process .ipynb files in the repository, convert to .py, summarize, and return docs."""
        
        # Parse the repository URL
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1]
        
        docs = []
        for notebook in notebooks:
            if notebook['name'].endswith('.ipynb'):
                try:
                    ipynb_content = self._get_github_file_content(owner, repo, notebook['path'])
                    nb = nbformat.reads(ipynb_content, as_version=4)
                    py_exporter = PythonExporter()
                    py_code, _ = py_exporter.from_notebook_node(nb)
                    # summary = self._summarize_notebook(py_code, notebook['name'])
                    summary = self._summarize_document(py_code, notebook['name'])
                    doc = {
                        "name": notebook['name'],
                        "type": "doc",
                        "file": notebook['path'],
                        "repo": f"{owner}/{repo}",
                        "docstring_header": summary,
                        "docstring": summary,
                        "source_code": py_code,
                    }
                    docs.append(doc)
                except Exception as e:
                    print(f"Error processing notebook {notebook['name']}: {e}")
        return docs
    
    def _process_rst(self, repo_url: str, rst_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process .rst files in the repository, extract content and headers."""
        
        # Parse the repository URL
        parsed_url = urlparse(repo_url)
        path_parts: list[str] = parsed_url.path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1]
        
        docs: list[dict[str, str | Any]] = []
        for rst in rst_files:
            if rst['name'].endswith('.rst'):
                try:
                    content: str = self._get_github_file_content(owner, repo, rst['path'])
                    summary: str = self._summarize_document(content, rst['name'])
                    doc: dict[str, str] = {
                        "name": rst['name'],
                        "type": "doc",
                        "file": rst['path'],
                        "repo": f"{owner}/{repo}",
                        "docstring_header": summary,
                        "docstring": summary,
                        "source_code": content,
                    }
                    docs.append(doc)
                except Exception as e:
                    print(f"Error processing rst file {rst['name']}: {e}")
        return docs
    
    def create_database(self, name: str, results: dict[str, Any]):
        """Create a new database collection and upload documentation."""

        # Create a collection
        self.client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=self.encoder.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE,
            ),
        )

        docs = results['results']
        readme_docs = results['readme_docs']

        if readme_docs:
            # Get repository info from the first doc
            repo_parts = docs[0]['repo'].split('/')
            owner, repo = repo_parts[0], repo_parts[1]
            
            # Get README content from the files dictionary
            readme_content = None
            files = self._get_github_files(owner, repo)
            if files['readme']:
                readme_content = self._get_github_file_content(owner, repo, files['readme'][0]['path'])
            
            # Create metadata point with README
            metadata_point = models.PointStruct(
                id=string_to_uuid("readme"),
                vector=[0.0] * (self.encoder.get_sentence_embedding_dimension() or 1),
                payload={
                    "type": "metadata",
                    "readme_content": readme_content if readme_content else "No README found",
                    "repository": f"{owner}/{repo}",
                    "repository_url": f"https://github.com/{owner}/{repo}",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_docs": len(docs)
                }
            )
            
            # Upload metadata point
            self.client.upsert(
                collection_name=name,
                points=[metadata_point]
            )

        if docs:
            # Upload the docs
            self.client.upload_points(
                collection_name=name,
                points=[
                    models.PointStruct(
                        id=idx, 
                        vector=self.encoder.encode(f'{doc["name"]}:\n{doc["docstring_header"]}').tolist(), 
                        payload=doc
                    )
                    for idx, doc in enumerate(docs)
                    if doc["docstring_header"]  # Skip if docstring_header is empty
                ],
            )
        return self.client.get_collections()
    
    def process_repository(self, repo_url: str, module_name: str | None = None, output_dir: str | None = None, verbose: bool = False, include_notebooks: bool = False, include_rst: bool = False, exclude_tests: bool = False) -> List[Dict[str, Any]]:
        """Process a GitHub repository and create its documentation database.
        
        Args:
            repo_url: URL of the GitHub repository to process
            module_name: Name of the module (optional)
            output_dir: Directory to save JSONL output (optional)
            verbose: Whether to print detailed information (optional)
            include_notebooks: Whether to include Jupyter notebooks (optional)
            include_rst: Whether to include .rst files (optional)
            exclude_tests: Whether to exclude test files and directories (optional)
            
        Returns:
            List of analyzed documentation items
        """

        self.module_name = module_name or repo_url.split('/')[-1]
        repo_name: str = repo_url.split('/')[-1]

        # Check if collection exists
        collections = self.client.get_collections()
        collection_names: list[str] = [collection.name for collection in collections.collections]
        
        if repo_name in collection_names:
            # raise ValueError(f"Collection '{repo_name}' already exists.")
            print(f"Collection '{repo_name}' already exists. Deleting it first...")
            self.client.delete_collection(repo_name)

        # Analyze the repository
        print(f"Analyzing repository: {repo_url}")
        results: dict[str, Any] = self.analyze_repository(
            repo_url, 
            include_notebooks=include_notebooks, 
            include_rst=include_rst,
            exclude_tests=exclude_tests
        )
        print(f"Found {len(results['results'])} documented items")
        
        # Save results to a JSONL file if output directory is specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            with open(os.path.join(output_dir, f'{repo_name}_docs.jsonl'), 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(json.dumps(item) + '\n')
        
        # Create the database
        self.create_database(repo_name, results)
        
        # Print results if verbose
        if verbose:
            for item in results['results']:
                print(f"\n{'='*80}")
                print(f"Name: {item['name']}")
                print(f"Type: {item['type']}")
                print(f"File: {item['file']}")
                print(f"Repository: {item['repo']}")
                print(f"\nDocstring Header:\n{item['docstring_header']}")
                print(f"\nFull Docstring:\n{item['docstring']}")
                print(f"\nSource Code:\n{item['source_code']}")
        
        return results

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description='Create documentation database for a GitHub repository')
    parser.add_argument('repo_url', help='GitHub repository URL')
    parser.add_argument('--output-dir', '-o', help='Directory to save JSONL output', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--include-notebooks', action='store_true', help='Include Jupyter notebooks')
    parser.add_argument('--include-rst', action='store_true', help='Include rst files')
    parser.add_argument('--exclude-tests', action='store_true', help='Exclude test files and directories')
    parser.add_argument('--db-path', help='Path to store the database', default=None)
    parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    parser.add_argument('--github-token', help='GitHub personal access token', default=None)
    parser.add_argument('--openai-api-key', help='OpenAI API key', default=None)
    args = parser.parse_args()

    env_github_token = os.environ.get('GITHUB_TOKEN')
    github_token = args.github_token or env_github_token
    if not github_token:
        print("Warning: No GitHub token provided or found in environment. Authentication may be limited.")

    openai_api_key = args.openai_api_key or os.environ.get('OPENAI_API_KEY')

    db = GitModuleHelpDB(
        db_path=args.db_path,
        qdrant_url=args.qdrant_url,
        github_token=github_token,
        openai_api_key=openai_api_key
    )
    db.process_repository(
        args.repo_url,
        output_dir=args.output_dir,
        verbose=args.verbose,
        include_notebooks=args.include_notebooks,
        include_rst=args.include_rst,
        exclude_tests=args.exclude_tests
    )