from typing import Literal

from pydantic import BaseModel, Field, field_validator



# USER
class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=30
    )

    password: str = Field(
        min_length=6,
        max_length=64
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str):
        value = value.strip()

        if not value.replace("_", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers and underscore"
            )

        return value


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: Literal["user", "admin"]


# TOKEN
class Token(BaseModel):
    access_token: str
    token_type: str


# WATCHLIST
class WatchlistCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=10
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str):
        value = value.strip().upper()

        if not value.isalnum():
            raise ValueError(
                "Stock symbol must contain only letters and numbers"
            )

        return value


class WatchlistResponse(BaseModel):
    id: int
    symbol: str

    class Config:
        from_attributes = True


# CHAT
class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000
    )

    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=10
    )


class ChatResponse(BaseModel):
    id: int
    question: str
    answer: str

    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100
    )

class ConversationUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=100
    )

class ConversationResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True

class StockAnalyzeRequest(BaseModel):
    question: str | None = Field(
        default=None,
        max_length=2000
    )

class StockAnalyzeRequest(BaseModel):
    question: str | None = Field(
        default=None,
        max_length=2000
    )