from fastapi import APIRouter
from Views.model import packageNameQuery
from Controllers.SchemaExtractor import SDKGroundingEngine

router=APIRouter(prefix="/userquery")

@router.get("/")
def breathingMessage():
    return {"message":"Server is Up and Running!!"}

@router.post("/process")
async def processUserQuery(request:packageNameQuery):

    packageName=request.packageName

    engine=SDKGroundingEngine()

    result=engine.process(packageName)

    return result