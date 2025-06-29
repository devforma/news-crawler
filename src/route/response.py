from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T")
class Response(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T]

    @classmethod
    def success(cls, data: T) -> "Response[T]":
        return cls(code=0, message="success", data=data)
    
    @classmethod
    def fail(cls, message: str) -> "Response[T]":
        return cls(code=1, message=message, data=None)