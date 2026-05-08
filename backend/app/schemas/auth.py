from pydantic import BaseModel

class LoginSchema(BaseModel):
    username: str
    senha: str
    