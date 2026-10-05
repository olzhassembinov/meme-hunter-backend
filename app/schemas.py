import uuid
from pydantic import BaseModel


class PlayerCreate(BaseModel):
    display_name: str


class PlayerOut(BaseModel):
    id: uuid.UUID
    display_name: str
    currency_balance: int
    level: int

    class Config:
        from_attributes = True

'''from_attributes = True lets this schema read directly off a SQLAlchemy Player object rather than requiring a plain dict — that's what lets you return player straight from a route below.'''