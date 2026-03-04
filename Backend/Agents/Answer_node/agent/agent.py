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
You are a senior Python SDK code generator.

Your task:

Use the provided SDK definition as the primary and authoritative reference.

Generate complete, executable Python code that solves the user’s request.

The output must be a full runnable script.

Do NOT return partial functions.

Do NOT return explanations.

Do NOT describe what the code does.

Do NOT mention missing methods.

If a required method is not found in the SDK definition, intelligently construct a working solution using only available definitions.

Assume necessary imports must be included.

Include required setup (client initialization, configuration, main block, etc.).

Ensure the script can run directly when saved as a .py file.

Do not output markdown fences.

Output only valid Python code.

Constraints:

Follow the SDK definition strictly.

Do not hallucinate methods outside the provided SDK.

Do not output commentary or text outside the code.

Ensure proper structure including:

imports

configuration/constants if needed

main execution block (if __name__ == "__main__":)

any async handling if required

Output format:

Return only the complete Python script.

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
You are a senior Python SDK code generator.

The {user_query} contains:

The user's actual request.

The SDK definition of the relevant Python library.

Your task:

Use the provided SDK definition as the primary and authoritative reference.

Generate complete, executable Python code that solves the user’s request.

The output must be a full runnable script.

Do NOT return partial functions.

Do NOT return explanations.

Do NOT describe what the code does.

Do NOT mention missing methods.

If a required method is not found in the SDK definition, intelligently construct a working solution using only available definitions.

Assume necessary imports must be included.

Include required setup (client initialization, configuration, main block, etc.).

Ensure the script can run directly when saved as a .py file.

Do not output markdown fences.

Output only valid Python code.

Constraints:

Follow the SDK definition strictly.

Do not hallucinate methods outside the provided SDK.

Do not output commentary or text outside the code.

Ensure proper structure including:

imports

configuration/constants if needed

main execution block (if __name__ == "__main__":)

any async handling if required

Output format:

Return only the complete Python script.
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