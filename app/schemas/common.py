from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    message: str


class Health(BaseModel):
    status: str
    environment: str
    database: str
    listing_provider: str
    price_model: str
