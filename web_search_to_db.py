from rag_code import EmbedData, QdrantVDB
import os
import ssl
import requests
from dotenv import load_dotenv
from tqdm import tqdm
from combined_search import CombinedSearcher
import json

class WebSearchIngestor:
    def __init__(self, collection_name="web_search_collection"):
        self.collection_name = collection_name
        self.setup_bright_data()
        self.setup_database()
        
    def setup_bright_data(self):
        # Load environment variables
        load_dotenv()
        
        # Configure SSL
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Bright Data configuration
        host = 'brd.superproxy.io'
        port = 33335
        self.username = os.getenv("BRIGHDATA_USERNAME")
        self.password = os.getenv("BRIGHDATA_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("Bright Data credentials not found in environment variables")
        
        proxy_url = f'http://{self.username}:{self.password}@{host}:{port}'
        self.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def setup_database(self):
        # Initialize embedding model
        self.embedder = EmbedData()
        
        # Initialize vector database
        self.database = QdrantVDB(self.collection_name)
        self.database.define_client()
        self.database.create_collection()
    
    def search_and_store(self, query, num_results=50):
        try:
            # Format query for URL
            formatted_query = "+".join(query.split())
            url = (
                f"https://www.google.com/search"
                f"?q={formatted_query}"
                f"&num={num_results}"
                f"&brd_json=1"
                f"&brd_results=1"
                f"&brd_serp=1"
            )
            
            # Add headers to make the request more browser-like
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Make search request
            response = requests.get(
                url, 
                proxies=self.proxies, 
                verify=False,
                headers=headers
            )
            
            # Check response status
            if response.status_code != 200:
                raise Exception(f"Search request failed with status code: {response.status_code}")
            
            try:
                results = response.json()
                if 'organic' in results:
                    results = results['organic']
                else:
                    print("Response content:", response.text[:500])  # Print first 500 chars of response
                    raise Exception("Unexpected response format - 'organic' key not found")
            except json.JSONDecodeError:
                print("Failed to parse JSON response. Response content:", response.text[:500])
                raise
            
            # Debug: Print raw results
            print("\nRaw search results:")
            for result in results[:2]:  # Print first 2 results for debugging
                print("\nResult:", result)
            
            # Prepare texts for embedding
            texts = []
            for result in results:
                # Extract fields with better error handling
                title = result.get('title', '')
                url = result.get('url', '')
                snippet = result.get('snippet', '')
                
                if not any([title, url, snippet]):
                    print(f"\nWarning: Empty result found: {result}")
                    continue
                
                # Debug: Print individual fields
                print("\nProcessing result:")
                print("Title:", title)
                print("URL:", url)
                print("Snippet:", snippet)
                
                text = f"Title: {title}\nURL: {url}\nSnippet: {snippet}"
                texts.append(text)
                
                # Debug: Print formatted text
                print("\nFormatted text:")
                print(text)
            
            if not texts:
                raise Exception("No valid results found to store")
            
            print(f"\nFound {len(texts)} search results. Generating embeddings...")
            
            # Generate embeddings
            self.embedder.embed(texts)
            
            print("Storing results in database...")
            # Store in database
            self.database.ingest_data(self.embedder)
            
            print(f"Successfully stored {len(texts)} search results in collection '{self.collection_name}'")
            return len(texts)
            
        except Exception as e:
            print(f"Error during search and store: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    ingestor = WebSearchIngestor()
    query = "machine learning best practices"
    num_results = ingestor.search_and_store(query)
    print(f"Stored {num_results} results for query: '{query}'")

    # Test the retrieval
    ingestor.search_and_store("machine learning best practices")

    # Test the retrieval using CombinedSearcher
    searcher = CombinedSearcher()
    results = searcher.search("machine learning best practices") 