import os 
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
from google.genai import types
from google.adk.tools.toolbox_toolset import ToolboxToolset
from pinecone import Pinecone
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


        pc.create_index_for_model(
        name=response['package'],
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
        )

        print(f'Index_For_Package_{response['package']}')

        schema=response['schema']
        package_name=response['package']

        chunks = await self.schema_to_chunks(schema, package_name)

        print(f"Upserting {len(chunks)} chunks...")

        dense_index = pc.Index(response['package'])
        
        dense_index.upsert_records("example-namespace", chunks)

        print("Upsert complete.")

        return {"Message":'Uploaded Chunks in Vector DB'}


    async def call_mcp_tools(self,package_name:str|None):

        client=Client(
            "http://localhost:9000/mcp"
        )

        async with client:
            result = await client.call_tool("call_Parser_Service", {"package_name":f"{package_name}"})
            return result.data['response']