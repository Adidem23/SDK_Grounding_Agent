from fastapi import APIRouter
from Views.model import userBackendQuery
from Controllers.client_class import Agent_Client_Class

router=APIRouter(prefix="/userquery")

@router.get("/")
def breathingMessage():
    return {"message":"Server is Up and Running!!"}

@router.post("/process")
async def processUserQuery(request:userBackendQuery):

    PARSER_NODE_BASE_URL="http://localhost:8005"
    
    user_query=request.userQuery

    new_client=Agent_Client_Class()

    response= await new_client.create_connection(PARSER_NODE_BASE_URL,user_query)

    if(response):
        return response 