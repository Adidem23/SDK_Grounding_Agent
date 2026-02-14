from pydantic import BaseModel

class packageNameQuery(BaseModel):
    packageName:str | None