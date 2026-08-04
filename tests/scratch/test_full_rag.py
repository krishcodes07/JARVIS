import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from jarvis.core.config import JarvisConfig
from jarvis.providers.manager import ProviderManager
from jarvis.memory.vector.embedder import Embedder
from jarvis.tools.rag import ToolRetriever
from jarvis.providers.base import ToolDefinition


async def main():
    config = JarvisConfig.load()
    provider_mgr = ProviderManager(config)
    provider_mgr.registry.load()
    
    embedder = Embedder(
        model=config.memory.vector.embedding_model,
        preferred_provider=config.memory.vector.embedding_provider,
        provider_manager=provider_mgr,
    )
    
    retriever = ToolRetriever(embedder=embedder)
    await retriever.initialize()
    
    sample_tools = [
        ToolDefinition(name="get_tools", description="List all available tools", parameters={}),
        ToolDefinition(name="screenshot", description="Capture display screenshot", parameters={}),
        ToolDefinition(name="calculator", description="Evaluate math expressions", parameters={}),
        ToolDefinition(name="run_command", description="Run terminal command", parameters={}),
        ToolDefinition(name="url_reader", description="Fetch website content", parameters={}),
    ]
    
    print("[1] Indexing tools with NVIDIA Embeddings...")
    await retriever.index_tools(sample_tools)
    
    print("[2] Retrieving tools for query 'take screenshot'...")
    results = await retriever.retrieve("take screenshot", sample_tools, top_k=2, always_include=["get_tools"])
    
    retrieved_names = [t.name for t in results]
    print(f"Retrieved tools: {retrieved_names}")
    
    if "screenshot" in retrieved_names and "get_tools" in retrieved_names:
        print("[SUCCESS] Tool RAG with NVIDIA Embeddings is working perfectly!")
    else:
        print("[FAIL] Retrieval result unexpected.")

if __name__ == "__main__":
    asyncio.run(main())
