import os 
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from google.adk.tools.toolbox_toolset import ToolboxToolset
from pinecone import Pinecone
from fastmcp import Client
from agent.client_class import Agent_Client_Class


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

        self.packageAgent=Agent(
            name="Package_Name_Extractor",
            model="gemini-2.5-flash",
            instruction=("""
You are a Python package name extraction engine.

Your task is to extract the most relevant Python package name mentioned or implied in the user query.

Rules:
- Return ONLY the package name.
- Output must be lowercase.
- Do not include explanations.
- Do not include extra words.
- Do not include punctuation.
- If no clear Python package can be identified, return: unknown
- If multiple packages are mentioned, return the most relevant one.

Examples:

User: how to upsert a collection in pinecone
Output: pinecone

User: how to create api using fastapi
Output: fastapi

User: how to send request using requests library
Output: requests

User: explain what is vector database
Output: unknown


""")
        )

    async def extractPythonModule(self,user_query:str|None):
       
        sessionService=InMemorySessionService()

        await sessionService.create_session(
            app_name="Package_Name_Extractor",
            user_id="user1",
            session_id="session1",
        )

        runner=Runner(
            app_name="Package_Name_Extractor",
            agent=self.packageAgent,
            session_service=sessionService,
        )

        user_message=types.Content(
            role="user",
            parts=[types.Part(text=user_query)]
        )

        async for event in runner.run_async(
            user_id="user1",
            session_id="session1",
            new_message=user_message
        ):
            
            if event.is_final_response():
                return event.content.parts[0].text
                

    async def call_mcp_tools(self,package_name:str|None,user_query:str|None):

        client=Client(
            "http://localhost:9000/mcp"
        )

        async with client:

            result = await client.call_tool("call_Parser_Service", {"package_name":f"{package_name}","user_query":user_query})

            return result
    
    async def delegateTasks(self, BASE_AGENT_URL:str|None , user_input:str|None):
       
        new_client=Agent_Client_Class()

        response= await new_client.create_connection(BASE_AGENT_URL,user_input)

        return response