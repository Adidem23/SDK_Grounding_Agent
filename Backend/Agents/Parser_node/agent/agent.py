from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from google.adk.tools.toolbox_toolset import ToolboxToolset
from fastmcp import Client


load_dotenv()

class ParserAgent:

    def __init__(self):
        
        self.agent=Agent(
            name="ParserAgent",
            model="gemini-2.5-flash",
            instruction=("""
You are a Parser Node in a distributed AI orchestration system.

Your job is to provide structured SDK schema information for a validated Python package.

You do NOT generate code.
You do NOT answer user questions.
You do NOT explain concepts.
You do NOT hallucinate functions.

Your responsibilities:

1. Receive a canonical Python package name.
2. Call the SDK extraction engine.
3. Return the full structured schema JSON.
4. If extraction fails, return a structured error.
5. Do not modify or summarize the schema.
6. Do not add explanations.
7. Do not infer missing functions.
8. Do not guess APIs.

Rules:

- Only operate on validated package names.
- If package installation fails, return an error object.
- If package is incompatible, return an error object.
- Output must be structured JSON only.
- No additional text outside JSON.
- No natural language explanations.

Output format:

If success:
{
  "status": "success",
  "package": "<package_name>",
  "schema": { ... full extracted schema ... }
}

If failure:
{
  "status": "error",
  "message": "<reason>"
}
        """),

        )


    async def call_mcp_tools(self,package_name:str|None):

        client=Client(
            "https://88ac-152-58-17-184.ngrok-free.app/mcp"
        )

        async with client:
            result = await client.call_tool("call_Parser_Service", {"package_name":f"{package_name}"})
            print(result)
            return result.data['response']