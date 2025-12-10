from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# -------------------------------------------------------------------
# AUTH MODELS  (UNCHANGED)
# -------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"  # "admin" | "editor" | "viewer"


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    role: str


# -------------------------------------------------------------------
# METHOD UPDATE MODEL
# -------------------------------------------------------------------

class UpdateMethodRequest(BaseModel):
    """
    Allows controlled updates to MADL documentation.
    Raw method code should be immutable after creation.
    """

    summary: Optional[str] = None
    description: Optional[str] = None
    intent: Optional[str] = None
    applies: Optional[str] = None
    returns: Optional[str] = None

    params: Optional[Dict[str, str]] = None
    keywords: Optional[List[str]] = None

    owner: Optional[str] = None
    example_usage: Optional[str] = None
    reusable: Optional[bool] = None


# -------------------------------------------------------------------
# SEARCH REQUEST
# -------------------------------------------------------------------

class SearchRequest(BaseModel):
    """
    Query schema for METHOD search.
    """

    query: str

    owner: Optional[str] = None
    reusable: Optional[bool] = None

    keywords: Optional[List[str]] = None

    ranking_variant: str = Field(
        default="A",
        description="A=original scoring, B=enhanced scoring",
    )


# -------------------------------------------------------------------
# SEARCH RESULT ITEM — METHOD VERSION
# -------------------------------------------------------------------

class SearchResultItem(BaseModel):
    """
    One ranked METHOD/MADL search result entry.
    """

    id: str
    probability: float

    method_name: str
    summary: str
    description: str
    intent: str

    params: Dict[str, str]
    applies: str
    returns: str

    keywords: List[str]

    owner: Optional[str] = None
    reusable: Optional[bool] = None
    example_usage: Optional[str] = None


# -------------------------------------------------------------------
# SEARCH RESPONSE
# -------------------------------------------------------------------

class SearchResponse(BaseModel):
    """
    Final API response payload for method search.
    """

    query: str

    results_count: int
    results: List[SearchResultItem]

    from_cache: bool

    ranking_variant: str
