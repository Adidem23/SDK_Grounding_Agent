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
        You are the Final Answer Agent in a distributed multi-agent system.

Your role is to generate the final code based output 

You recieve:
- The original user query
- A validated SDK schema JSON (optional)

Rules:

   - Use ONLY functions and classes present in the schema.
   - Do NOT hallucinate APIs.
   - Do NOT invent functions.
   - Follow the exact method signatures.
   - Respect the documented parameters.

3. Always produce:
   - Clean
   - Minimal
   - Production-ready code
   - No unnecessary commentary

4. Do NOT:
   - Mention internal system nodes
   - Mention parser node
   - Mention supervisor
   - Mention schema extraction
   - Output JSON
   - Output reasoning

5. If information is insufficient, make safe assumptions but do not hallucinate unknown SDK functions.

Output format:
Return only code for the given user query.
No explanations.
No metadata.
No JSON.
 """),

        )


    async def retriveContext(self,user_query:str | None):
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY",""))

        existing_indexes = [i.name for i in pc.list_indexes()]

        index=existing_indexes[0]

        results = index.search(
            query={
                "top_k": 20,
                "inputs": {
                    "text": user_query
                }
            },
            filter={"package": "opik"},
            include_metadata=True
        )

        return results


    async def giveFinalAnswer(self,user_query:str|None):

        retrived_context=await self.retriveContext(user_query)

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
with the help of {retrived_context} and {user_query}
create the final code do not hallucinate and do not invent functions which are not mentioned in conetxt . Strict to context only and give python code""")]

        )

        async for event in runner.run_async(
            user_id="user1",
            session_id="session1",
            new_message=user_message
        ):
            
            if event.is_final_response():
                print(event.content.parts[0].text)
                return event.content.parts[0].text