import argparse
from qdrant_client import QdrantClient

class QdrantLister:
    """A class for listing collections in a Qdrant database."""
    
    def __init__(self, qdrant_url: str = 'http://localhost:6333'):
        """Initialize the QdrantLister instance.
        
        Args:
            qdrant_url: URL of the Qdrant server (default: 'http://localhost:6333')
        """
        self.qdrant_url = qdrant_url
        self.client = QdrantClient(qdrant_url)
    
    def list_collections(self) -> list:
        """List all collections in the Qdrant database.
        
        Returns:
            List of collection names
        """
        collections = self.client.get_collections()
        return [collection.name for collection in collections.collections]

def main():
    parser = argparse.ArgumentParser(description='List Qdrant database collections')
    parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    args = parser.parse_args()
    
    lister = QdrantLister(qdrant_url=args.qdrant_url)
    collections = lister.list_collections()
    
    if collections:
        print("Collections in Qdrant:")
        for collection in collections:
            print(f"- {collection}")
    else:
        print("No collections found in Qdrant.")

if __name__ == "__main__":
    main()