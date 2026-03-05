import os
import asyncio
import time
from dotenv import load_dotenv
from Schema_Extractor import SDKGroundingEngine


load_dotenv()


async def run_code():
      engine=SDKGroundingEngine()
      engine.load_package("langchain-mcp-adapters")
      response=engine.search("langchain-mcp-adapters","how to use load_mcp_tools in langchain_mcp_adapters")
      print(response)
      

if __name__=="__main__":
      asyncio.run(run_code())