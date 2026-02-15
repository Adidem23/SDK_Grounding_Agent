from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from agent.client_class import Agent_Client_Class

load_dotenv()

class SupervisorAgent:

    def __init__(self):
        self.agent=Agent(
            name="SupervisorAgent",
            model="gemini-2.5-flash",
            instruction=("""
      You are a strict Python package extraction agent.

Your task is to extract the Python package name mentioned in the user query.

Rules:

- If the query contains phrases like:
  "using <name>"
  "with <name>"
  "in <name>"
  "via <name>"
  treat <name> as a potential Python package.
- Extract that name exactly as written, converted to lowercase.
- Do not invent packages.
- Do not guess unrelated names.
- Do not return explanations.
- If no potential package name is present, return: NONE
- If multiple names are present, return the primary one.

Output format:
Return only the package name as a plain lowercase string.
          
            """)
        )
 
    async def extractPythonModule(self,user_query:str|None):
       
        sessionService=InMemorySessionService()

        await sessionService.create_session(
            app_name="Supervisor_Agent",
            user_id="user1",
            session_id="session1",
        )

        runner=Runner(
            app_name="Supervisor_Agent",
            agent=self.agent,
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
    

    async def delegateTasks(self, BASE_AGENT_URL:str|None , user_input:str|None):
       
        new_client=Agent_Client_Class()

        response= await new_client.create_connection(BASE_AGENT_URL,user_input)

        return response