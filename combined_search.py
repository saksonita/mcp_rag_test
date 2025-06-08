from rag_code import EmbedData, QdrantVDB, Retriever

class CombinedSearcher:
    def __init__(self):
        # Initialize embedding model
        self.embedder = EmbedData()
        
        # Initialize both databases
        self.ml_faq_db = QdrantVDB("ml_faq_collection")
        self.ml_faq_db.define_client()
        
        self.web_db = QdrantVDB("web_search_collection")
        self.web_db.define_client()
        
        # Initialize retrievers
        self.ml_faq_retriever = Retriever(self.ml_faq_db, self.embedder)
        self.web_retriever = Retriever(self.web_db, self.embedder)
    
    def search(self, query):
        print("\nSearching ML FAQ collection...")
        try:
            faq_results = self.ml_faq_retriever.search(query)
            print("\nML FAQ Results:")
            print(faq_results)
        except Exception as e:
            print(f"Error searching ML FAQ: {str(e)}")
            faq_results = "No results found in ML FAQ"
        
        print("\nSearching web results collection...")
        try:
            web_results = self.web_retriever.search(query)
            print("\nWeb Search Results:")
            print(web_results)
        except Exception as e:
            print(f"Error searching web results: {str(e)}")
            web_results = "No results found in web search"
        
        return {
            "faq_results": faq_results,
            "web_results": web_results
        }

if __name__ == "__main__":
    # Example usage
    searcher = CombinedSearcher()
    query = "What is overfitting in machine learning?"
    results = searcher.search(query)
    
    print("\nCombined Search Results:")
    print("\nFrom ML FAQ:")
    print(results["faq_results"])
    print("\nFrom Web Search:")
    print(results["web_results"]) 