import argparse
import os
from dotenv import load_dotenv
import qdrant_client
from qdrant_client import models

class QdrantCleaner:
    """A class for cleaning up Qdrant database collections.
    
    This class provides functionality to delete collections from a Qdrant database.
    """
    
    def __init__(self, qdrant_url: str = 'http://localhost:6333'):
        """Initialize the QdrantCleaner instance.
        
        Args:
            qdrant_url: URL of the Qdrant server (default: 'http://localhost:6333')
        """
        self.qdrant_url = qdrant_url
        self.client = qdrant_client.QdrantClient(qdrant_url)
    
    def delete_all_collections(self) -> list:
        """Delete all collections from the Qdrant database.
        
        Returns:
            List of deleted collection names
        """
        collections = self.client.get_collections()
        deleted_collections = []
        
        for collection in collections.collections:
            collection_name = collection.name
            self.client.delete_collection(collection_name)
            deleted_collections.append(collection_name)
        
        return deleted_collections
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a specific collection from the Qdrant database.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if collection was deleted, False otherwise
        """
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {str(e)}")
            return False

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Clean Qdrant database collections')
    parser.add_argument('--qdrant-url', help='Qdrant server URL', default='http://localhost:6333')
    parser.add_argument('--collection', help='Specific collection to delete (optional, if not provided, all collections will be deleted)')
    args = parser.parse_args()
    
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

if __name__ == "__main__":
    main() 