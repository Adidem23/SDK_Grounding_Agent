import asyncio
from fastmcp import Client


async def call_mcp_tools():

    client=Client(
        "http://localhost:9000/mcp"
    )

    async with client:
        result = await client.call_tool("call_Parser_Service", {"package_name": "fastapi","user_query":"how to use CORSmiddleWare in fastapi"})
        print(result)


if __name__=="__main__":
    asyncio.run(call_mcp_tools())