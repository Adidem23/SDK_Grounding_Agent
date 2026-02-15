import httpx
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP("Parser_Service_MCP")


@mcp.tool()
async def call_Parser_Service(package_name: str | None):
    """
    Calls Parser_service api 
    and forwards the package_name.
    """

    url = "http://localhost:8900/userquery/process"

    payload = {
        "packageName": package_name
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)

        return {
            "status_code": response.status_code,
            "response": response.json()
        }

    except Exception as e:
        return {
            "error": str(e)
        }


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

http_app=mcp.http_app(middleware=middleware)