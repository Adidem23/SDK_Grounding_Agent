import os
import asyncio
import time
from dotenv import load_dotenv
from pinecone import Pinecone
from Schema_Extractor import SDKGroundingEngine


load_dotenv()


async def run_code():
      engine=SDKGroundingEngine()
      engine.load_package("opik")
      response=engine.search("opik","how to use traces in opik")
      print(response)
      final_response=await uploadSDKSchemaToPinecone("opik",response)
      print(final_response)
      

def truncate_text(text, max_chars=1500):
        if not text:
            return "No description available."
        return text[:max_chars]
            

async def schema_to_chunks(results: list, package_name: str):
    """
    results: list of dicts with keys:
        - class_path
        - description
        - methods
    """

    chunks = []
    seen_class_names = set()
    MAX_CHARS = 3500

    for item in results:

        class_path = item.get("class_path")
        description = truncate_text(item.get("description"), 1200)
        methods = item.get("methods", {})

        class_name = class_path.split(".")[-1]
        module_name = class_path.rsplit(".", 1)[0]

        # 🔥 Deduplicate logical classes (important!)
        if class_name in seen_class_names:
            continue
        seen_class_names.add(class_name)

        header = f"""
SDK Documentation

Package: {package_name}
Full Path: {class_path}
Type: Class
Class Name: {class_name}
Module: {module_name}

Description:
{description}

Methods:
"""

        class_content = header
        part_counter = 1

        for method_name, method_data in methods.items():

            signature = truncate_text(method_data.get("signature"), 400)
            method_desc = truncate_text(method_data.get("description"), 700)

            method_block = f"""
--------------------------------
Method Name: {method_name}

Signature:
{signature}

Description:
{method_desc}
"""

            # Split if too large
            if len(class_content) + len(method_block) > MAX_CHARS:
                chunks.append({
                    "_id": f"{package_name}:{class_path}:part{part_counter}",
                    "chunk_text": class_content.strip()
                })

                part_counter += 1
                class_content = header  # restart new chunk

            class_content += method_block

        # Final flush
        if class_content.strip():
            chunks.append({
                "_id": f"{package_name}:{class_path}:part{part_counter}",
                "chunk_text": class_content.strip()
            })

    print(f"📦 Final chunk count: {len(chunks)}")
    return chunks

async def batch_upsert(index, records, namespace, batch_size=100):
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        index.upsert_records(namespace, batch)
        await asyncio.sleep(1)  

async def uploadSDKSchemaToPinecone(package_name,response):
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY",""))

        pc.create_index_for_model(
        name=package_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
        )

        print(f'Index_For_Package_{package_name}')

        chunks = await schema_to_chunks(response, package_name)

        print(f"Upserting {len(chunks)} chunks...")

        dense_index = pc.Index(package_name)

        await batch_upsert(
        dense_index,
        chunks,
        namespace="example-namespace",
        batch_size=59)

        print("Upsert complete.")

        return {"Message":'Uploaded Chunks in Vector DB'}


if __name__=="__main__":
      asyncio.run(run_code())