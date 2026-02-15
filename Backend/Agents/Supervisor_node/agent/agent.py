import os
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from agent.client_class import Agent_Client_Class
from pinecone import Pinecone

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
            

    def truncate_text(self,text, max_chars=1500):
        if not text:
            return "No description available."
        return text[:max_chars]
            

    async def schema_to_chunks(self,schema: dict, package_name: str):
        chunks = []

        for class_path, class_data in schema.items():
            class_name = class_path.split(".")[-1]
            module_name = class_data.get("module")
            class_description = self.truncate_text(class_data.get("description"))


            class_chunk_text = f"""
            SDK Documentation

            Package: {package_name}
            Type: Class
            Class Name: {class_name}
            Module: {module_name}

            Description:
            {class_description}
            """

            chunks.append({
                "id": f"{package_name}:{class_name}",
                "chunk_text": class_chunk_text.strip(),
                "metadata": {
                    "package": package_name,
                    "type": "class",
                    "class": class_name,
                    "module": module_name
                }
            })

            methods = class_data.get("methods", {})

            for method_name, method_data in methods.items():
                signature = self.truncate_text(method_data.get("signature"))
                description = self.truncate_text(method_data.get("description"))

                method_chunk_text = f"""
                SDK Documentation

                Package: {package_name}
                Type: Method
                Class Name: {class_name}
                Method Name: {method_name}

                Signature:
                {signature}

                Description:
                {description}
                """

                chunks.append({
                    "id": f"{package_name}:{class_name}:{method_name}",
                    "chunk_text": method_chunk_text.strip(),
                    "metadata": {
                        "package": package_name,
                        "type": "method",
                        "class": class_name,
                        "method": method_name,
                        "module": module_name
                    }
                })

        return chunks

    async def uploadSDKSchemaToPinecone(self,response):
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY",""))

        index_name = f'Index_For_Package_{response['pacakge']}'

        pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
        )

        print(f'Index_created for {index_name}')

        schema=response['schema']
        package_name=response['package']

        chunks = await self.schema_to_chunks(schema, package_name)

        print(f"Upserting {len(chunks)} chunks...")

        index_name.upsert(chunks)

        print("Upsert complete.")

        return {"Message":'Uploaded Chunks in Vector DB'}
    

    async def delegateTasks(self, BASE_AGENT_URL:str|None , user_input:str|None):
       
        new_client=Agent_Client_Class()

        response= await new_client.create_connection(BASE_AGENT_URL,user_input)

        return response