import logging
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from .config import Settings

logger = logging.getLogger(__name__)

class SearchClient:
    """Client for interacting with Azure AI Search."""
    
    # Initialize the search client with the provided settings
    def __init__(self, settings: Settings):
        """Initialize the search client with the provided settings."""
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.key = settings.AZURE_SEARCH_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX_NAME
        self.client = None
        self._init_client()
    
    # Initialize the Azure AI Search client
    def _init_client(self):
        """Initialize the Azure AI Search client."""
        try:
            credential = AzureKeyCredential(self.key)
            self.client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=credential
            )
            logger.info(f"Initialized Azure AI Search client with index {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure AI Search client: {e}")
            raise
    
    # Search for documents using the provided search text
    def search_documents(self, search_text: str, top: int = 5) -> List[Dict[str, Any]]:
        """Search for documents using the provided search text."""
        try:
            results = self.client.search(
                search_text=search_text,
                top=top,
                include_total_count=True
            )
            return [doc for doc in results]
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    # Upload a document to the search index
    def upload_document(self, document: Dict[str, Any]) -> bool:
        """Upload a document to the search index."""
        try:
            self.client.upload_documents(documents=[document])
            return True
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return False
    
    # Delete a document from the search index
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the search index."""
        try:
            self.client.delete_documents(documents=[{"id": document_id}])
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    # Check if the search client is available
    def is_available(self) -> bool:
        """Check if the search client is available and properly initialized."""
        return hasattr(self, 'client') and self.client is not None 