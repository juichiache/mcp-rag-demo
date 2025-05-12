#!/usr/bin/env python
import os
import logging
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient as AsyncSearchClient
from azure.search.documents.indexes.aio import SearchIndexClient as AsyncSearchIndexClient

from mcp.server.fastmcp import FastMCP

# Enable debug logging
# logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Azure Cognitive Search configuration
endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")

# Validate configuration
if not all([endpoint, index_name, admin_key]):
    logging.error("Missing Azure Search configuration: "
                  f"endpoint={endpoint}, index_name={index_name}, admin_key={'set' if admin_key else 'None'}")
    raise SystemExit("Azure Search configuration incomplete.")

# Instantiate async Azure Search clients
search_client = AsyncSearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(admin_key)
)
index_client = AsyncSearchIndexClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(admin_key)
)

# Create MCP server
mcp = FastMCP("azure-search-mcp-server")

@mcp.tool()
async def search(query: str, top: int = 3) -> list[dict]:
    """Search documents in the configured index."""
    logging.debug(f"[Server] search tool invoked with query={query!r}, top={top}")
    results = []
    try:
        results_paged = await search_client.search(search_text=query, top=top)
        async for doc in results_paged:
            results.append(dict(doc))
        logging.debug(f"[Server] search -> returning {len(results)} documents")
    except Exception:
        logging.exception("[Server] search failed")
    return results

if __name__ == "__main__":
    # Run the MCP server over SSE on port 8000
    mcp.run(transport="sse")