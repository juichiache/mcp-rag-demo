import os
import asyncio
import logging
from openai import AzureOpenAI
#from mcp import ClientSession as cs
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from dotenv import load_dotenv
from pprint import pprint
import json

# Enable debug logging
# tt=logging.basicConfig(level=logging.DEBUG)

# Load .env file if present
load_dotenv()

async def search_docs(session, query, top=3):
    # call the MCP search tool
    tool_resp = await session.call_tool(
        "search",
        arguments={"query": query, "top": top}
    )

    # bail out if the tool returned an error
    if getattr(tool_resp, "isError", False):
        raise RuntimeError(f"search tool error: {tool_resp}")

    # tool_resp.content is a list of TextContent(type='text', text='<json-string>')
    hits = getattr(tool_resp, "content", [])

    docs = []
    for hit in hits:
        raw = getattr(hit, "text", "")
        try:
            # parse the JSON string and pull out its "content" field
            obj = json.loads(raw)
            chunk = obj.get("content", "")
        except json.JSONDecodeError:
            # if it wasn’t valid JSON for some reason, just use the raw blob
            chunk = raw

        docs.append(chunk)

    return docs

def generate_answer(openai_client, docs, query):
    # docs is a list of dicts, so use ["content"]
    context = "\n\n".join(docs)
    prompt = f"Use the following context to answer the question:\n{context}\n\nQuestion: {query}"
    # print("\nfull prompt:\n", prompt)

    response = openai_client.chat.completions.create(
        stream=False,  # set to True if you want streaming
        messages=[
            {"role": "system",  "content": "You are a helpful assistant that answers user queries grounded in provided context. Respond with a concise answer and a reference to the source if the answer exists in the knowledge source. If the answer is not found in the source, respond with 'I don't know.'"},
            {"role": "user",    "content": prompt}
        ],
        max_completion_tokens=800,
        temperature=1.0,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        model="gpt-4.1"
    )
    return response.choices[0].message.content

async def run_rag():
    # 1. Configure Azure OpenAI client
    endpoint = "https://jc-azureaistudio-aiservices.cognitiveservices.azure.com/"
    model_name = "gpt-4.1"
    deployment = "gpt-4.1"

    subscription_key = "1c0f8ed07f7b439b9730832e53470eae"
    api_version = "2024-12-01-preview"
    openai_client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        api_key=subscription_key
    )

    # 2. Build your MCP SSE URL
    mcp_url = os.environ["MCP_ENDPOINT"].rstrip("/") + "/sse"

    # 3. Open SSE transport and MCP session
    async with sse_client(mcp_url) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            # 4. Get user query
            query = input("Enter your query: ")

            # 7. Retrieve docs
            docs = await search_docs(session, query)
            # DEBUG: inspect what docs contains
            # print("\n[DEBUG] raw docs received:")
            # pprint(docs)
            # print(f"[DEBUG] docs is a {type(docs).__name__} with {len(docs)} items\n")

            # 8. Generate answer via Azure OpenAI
            answer = generate_answer(openai_client, docs, query)

            print("\nAnswer:\n", answer)

if __name__ == "__main__":
    asyncio.run(run_rag())
