from pydantic import BaseModel


class UserStatusUpdate(BaseModel):
    is_active: bool
