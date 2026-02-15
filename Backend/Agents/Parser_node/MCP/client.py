import asyncio
from fastmcp import Client


async def call_mcp_tools():

    client=Client(
        "https://88ac-152-58-17-184.ngrok-free.app/mcp"
    )

    async with client:
        result = await client.call_tool("call_Parser_Service", {"package_name": dotenv})
        print(type(result.data["response"]))


if __name__=="__main__":
    asyncio.run(call_mcp_tools())