from typing import Annotated, TypeVar, Generic, Optional
from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel

@dataclass
class Pagination():
    page: Annotated[Optional[int], Query(gt=0)] = 1
    limit: Annotated[Optional[int], Query(gt=0, le=100)] = 15


T = TypeVar("T")

class Paginated(BaseModel, Generic[T]):
    total_results: int
    total_pages: int
    current_page: int
    results: list[T]

