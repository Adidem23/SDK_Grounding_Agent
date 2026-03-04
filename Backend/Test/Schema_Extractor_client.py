import os
import asyncio
import time
from dotenv import load_dotenv
from Schema_Extractor import SDKGroundingEngine


load_dotenv()


async def run_code():
      engine=SDKGroundingEngine()
      engine.load_package("fastapi")
      response=engine.search("fastapi","how to use CORS_Middleware in fastapi")
      print(response)
      

if __name__=="__main__":
      asyncio.run(run_code())