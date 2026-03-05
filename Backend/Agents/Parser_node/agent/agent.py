import os
import re
import requests
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from fastmcp import Client
from agent.client_class import Agent_Client_Class

load_dotenv()


class ParserAgent:

    def __init__(self):

        self.agent = Agent(
            name="ParserAgent",
            model="gemini-2.5-flash",
            instruction="""
You are a Parser Node in a distributed AI orchestration system.

Your job is to provide structured SDK schema information for a validated Python package.

Rules:
- Only operate on validated package names.
- Output must be structured JSON only.
- No explanations.
"""
        )

        self.packageAgent = Agent(
            name="Package_Name_Extractor",
            model="gemini-2.5-flash",
            instruction="""
You are a Python package name extraction engine.

Rules:
- Return ONLY the package name.
- Output must be lowercase.
- No explanations.
- If no package exists return: unknown
"""
        )

    # -------------------------
    # Utility Functions
    # -------------------------

    def normalize_package_name(self, pkg: str | None):

        if not pkg:
            return None

        pkg = pkg.strip().lower()
        pkg = pkg.replace(".", "")
        pkg = pkg.replace(",", "")
        pkg = pkg.replace("`", "")
        pkg = pkg.replace("'", "")

        return pkg

    def validate_package(self, pkg: str):

        if not pkg or pkg == "unknown":
            return False

        try:
            url = f"https://pypi.org/pypi/{pkg}/json"
            response = requests.get(url, timeout=3)

            return response.status_code == 200
        except Exception:
            return False

    def regex_extract_package(self, query: str):

        if not query:
            return None

        match = re.search(r"in ([a-zA-Z0-9_]+)", query.lower())

        if match:
            return match.group(1)

        return None

    # -------------------------
    # LLM Extraction
    # -------------------------

    async def extractPythonModule(self, user_query: str | None):

        sessionService = InMemorySessionService()

        await sessionService.create_session(
            app_name="Package_Name_Extractor",
            user_id="user1",
            session_id="session1",
        )

        runner = Runner(
            app_name="Package_Name_Extractor",
            agent=self.packageAgent,
            session_service=sessionService,
        )

        user_message = types.Content(
            role="user",
            parts=[types.Part(text=user_query)]
        )

        async for event in runner.run_async(
                user_id="user1",
                session_id="session1",
                new_message=user_message
        ):

            if event.is_final_response():

                raw_output = event.content.parts[0].text

                # Normalize
                pkg = self.normalize_package_name(raw_output)

                # Validate via PyPI
                if self.validate_package(pkg):
                    return pkg

                # Regex fallback
                fallback = self.regex_extract_package(user_query)

                if fallback and self.validate_package(fallback):
                    return fallback

                return "unknown"

    # -------------------------
    # MCP Tool Call
    # -------------------------

    async def call_mcp_tools(self, package_name: str | None, user_query: str | None):

        if package_name == "unknown":
            return {
                "status": "error",
                "message": "Python package could not be identified"
            }

        client = Client("http://localhost:9000/mcp")

        async with client:

            result = await client.call_tool(
                "call_Parser_Service",
                {
                    "package_name": package_name,
                    "user_query": user_query
                }
            )

            return result

    # -------------------------
    # Delegate to Answer Agent
    # -------------------------

    async def delegateTasks(self, BASE_AGENT_URL: str | None, user_input: str | None):

        new_client = Agent_Client_Class()

        response = await new_client.create_connection(
            BASE_AGENT_URL,
            user_input
        )

        return response