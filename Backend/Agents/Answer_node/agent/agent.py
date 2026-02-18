import os 
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from pinecone import Pinecone

load_dotenv()

class FinalAnswerAgent:

    def __init__(self):
        
        self.agent=Agent(
            name="FinalAnswerAgent",
            model="gemini-2.5-flash",
            instruction=(f"""
your task is to generate python code with given instruction provided in prompt

"""),

        )

    async def giveFinalAnswer(self,user_query:str|None):

        sessionService=InMemorySessionService()

        await sessionService.create_session(
            app_name="Final_Answer_Agent",
            user_id="user1",
            session_id="session1",
        )

        runner=Runner(
            app_name="Final_Answer_Agent",
            agent=self.agent,
            session_service=sessionService,
        )

        user_message=types.Content(
            role="user",
            parts = [types.Part(text=f"""
The {user_query} contains both has both user query and the sdk defination of the python library which user is asking with the help of the context of provided sdk defination generate the python code for the user query and return it 
""")]

        )

        async for event in runner.run_async(
            user_id="user1",
            session_id="session1",
            new_message=user_message
        ):
            
            if event.is_final_response():
                
                print(event.content.parts[0].text)

                return event.content.parts[0].text