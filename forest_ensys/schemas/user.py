from typing import Optional

from pydantic import BaseModel


# Shared attributes
class UserBase(BaseModel):
    username: Optional[str] = None


# Attributes to receive via API on creation
class UserCreate(UserBase):
    username: str
    password: str


# Attributes to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True


# Additional properties to return via API
class User(UserInDBBase):
    pass


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
