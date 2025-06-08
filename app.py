from quart import Quart, render_template, request, jsonify
from mcp.server.fastmcp import FastMCP
from rag_code import *
import asyncio
import threading
import httpx
import json

app = Quart(__name__)

# Create MCP server
mcp = FastMCP(
    name="MCP-RAG-app"
)

@mcp.tool()
async def machine_learning_faq_retrieval_tool(query: str) -> str:
    """Retrieve ML FAQ answers."""
    retriever = Retriever(QdrantVDB("ml_faq_collection"), EmbedData())
    return retriever.search(query)

@mcp.tool()
async def bright_data_web_search_tool(query: str) -> list[str]:
    """Search web using Bright Data."""
    import os
    import ssl
    from dotenv import load_dotenv

    load_dotenv()
    ssl._create_default_https_context = ssl._create_unverified_context

    # Check credentials
    username = os.getenv("BRIGHDATA_USERNAME")
    password = os.getenv("BRIGHDATA_PASSWORD")
    
    if not username or not password:
        raise ValueError("Bright Data credentials not found in .env file. Please set BRIGHDATA_USERNAME and BRIGHDATA_PASSWORD.")

    host = 'brd.superproxy.io'
    port = 33335

    # Configure proxy with httpx format
    proxy = f"http://{username}:{password}@{host}:{port}"

    formatted_query = "+".join(query.split())
    url = f"https://www.google.com/search?q={formatted_query}&brd_json=1&num=50"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        async with httpx.AsyncClient(proxy=proxy, verify=False, headers=headers, timeout=30.0) as client:
            response = await client.get(url)
            
            # Check response status
            if response.status_code != 200:
                raise ValueError(f"Search request failed with status code: {response.status_code}")
            
            try:
                data = response.json()
                print(f"Response data: {json.dumps(data, indent=2)[:500]}...")  # Debug print
                
                if 'organic' not in data:
                    raise ValueError(f"Unexpected API response format - 'organic' key not found. Response: {json.dumps(data, indent=2)[:500]}...")
                
                return data['organic']
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON response. Response content: {response.text[:500]}...")
            
    except httpx.RequestError as e:
        raise ValueError(f"Request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Web search error: {str(e)}")

@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/search', methods=['POST'])
async def search():
    data = await request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    faq_results = None
    web_results_str = None
    errors = []

    # Get FAQ results
    try:
        faq_results = await machine_learning_faq_retrieval_tool(query)
    except Exception as e:
        print(f"FAQ search error: {str(e)}")
        errors.append(f"FAQ search failed: {str(e)}")

    # Get web results
    try:
        web_results = await bright_data_web_search_tool(query)
        formatted_web_results = []
        for result in web_results[:3]:  # Take top 3 results
            text = (
                f"Title: {result.get('title', '')}\n"
                f"URL: {result.get('url', '')}\n"
                f"Snippet: {result.get('snippet', '')}"
            )
            formatted_web_results.append(text)
        web_results_str = "\n\n---\n\n".join(formatted_web_results)
    except Exception as e:
        print(f"Web search error: {str(e)}")
        errors.append(f"Web search failed: {str(e)}")

    # Return whatever results we have
    response = {
        'faq_results': faq_results if faq_results is not None else "FAQ search failed",
        'web_results': web_results_str if web_results_str is not None else "Web search failed",
        'errors': errors if errors else None
    }
    
    # Only return 500 if both searches failed
    if faq_results is None and web_results_str is None:
        return jsonify(response), 500
    return jsonify(response)

def run_mcp_server():
    """Run the MCP server in a separate thread"""
    mcp.run(transport="stdio")

if __name__ == '__main__':
    print("Starting Quart app with MCP integration")
    # Start MCP server in a separate thread
    mcp_thread = threading.Thread(target=run_mcp_server)
    mcp_thread.daemon = True
    mcp_thread.start()
    
    # Start Quart app in main thread
    app.run(debug=True, port=5000) 