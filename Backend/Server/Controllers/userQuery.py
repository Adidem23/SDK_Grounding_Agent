import os 
from dotenv import load_dotenv
from fastapi import APIRouter
from Views.model import userBackendQuery
from Controllers.client_class import Agent_Client_Class

load_dotenv()

SUPERVISOR_NODE_BASE_URL=os.getenv("SUPERVISOR_NODE_BASE_URL","http://localhost:8004")

router=APIRouter(prefix="/userquery")

@router.get("/")
def breathingMessage():
    return {"message":"Server is Up and Running!!"}

@router.post("/process")
async def processUserQuery(request:userBackendQuery):
    
    user_query=request.userQuery

    new_client=Agent_Client_Class()

    response= await new_client.create_connection(SUPERVISOR_NODE_BASE_URL,user_query)

    if(response):
        return response 