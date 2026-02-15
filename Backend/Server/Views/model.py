from pydantic import BaseModel

class userBackendQuery(BaseModel):
    userQuery:str | None