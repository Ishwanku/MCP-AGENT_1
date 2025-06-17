import logging
from typing import List, Dict, Any
from azure.search.documents import SearchClient as AzureSDKSearchClient
from azure.core.credentials import AzureKeyCredential
from .config import Settings

logger = logging.getLogger(__name__)

# Wrapper class for Azure Cognitive Search operations
class AzureSearchClient:
    """Client for interacting with Azure AI Search."""
    
    # Initialize the search client with the provided settings
    def __init__(self, settings: Settings):
        """
        Initialize the search client with the provided settings.
        Reads endpoint, API key, and index name from settings and creates the Azure Search client.
        """
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT  # Azure Search endpoint URL
        self.key = settings.AZURE_SEARCH_KEY           # Azure Search API key
        self.index_name = settings.AZURE_SEARCH_INDEX_NAME  # Index name to use
        self.client = None                             # Will hold the Azure SDK client instance
        self._init_client()                            # Initialize the Azure SDK client
    
    # Initializethe Azure AI Search client
    def _init_client(self):
        """
        Initialize the Azure AI Search client using the Azure SDK.
        Sets up authentication and connects to the specified index.
        """
        try:
            credential = AzureKeyCredential(self.key)  # Create credentials object
            self.client = AzureSDKSearchClient(
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
        """
        Search for documents using the provided search text.
        Args:
            search_text (str): The text to search for in the index.
            top (int): Maximum number of results to return.
        Returns:
            List[Dict[str, Any]]: List of matching documents.
        """
        try:
            results = self.client.search(
                search_text=search_text,
                top=top,
                include_total_count=True
            )
            return [doc for doc in results]  # Convert results to a list of dicts
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    # Upload a document to the search index
    def upload_document(self, document: Dict[str, Any]) -> bool:
        """
        Upload a document to the search index.
        Args:
            document (Dict[str, Any]): The document to upload (as a dictionary).
        Returns:
            bool: True if upload succeeded, False otherwise.
        """
        try:
            self.client.upload_documents(documents=[document])
            return True
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return False
    
    # Check if the search client is available
    def is_available(self) -> bool:
        """
        Check if the search client is available and properly initialized.
        Returns:
            bool: True if the client is ready to use, False otherwise.
        """
        return hasattr(self, 'client') and self.client is not None