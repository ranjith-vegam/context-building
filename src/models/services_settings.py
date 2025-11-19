from typing import Optional
from pydantic import BaseModel, field_validator
import json

# Reusable LLMArgs model
class LLMArgs(BaseModel):
    temperature: Optional[float] = None
    seed: Optional[int] = None
    response_format: Optional[dict] = None

    @field_validator("response_format", mode="before")
    def parse_response_format(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

class Layer1Settings(BaseModel):
    prompt_filepath: str
    llm_args: Optional[LLMArgs] = None

class Layer2Settings(BaseModel):
    prompt_filepath: str
    llm_args: Optional[LLMArgs] = None
    
class Layer3Settings(BaseModel):
    prompt_filepath: str
    llm_args: Optional[LLMArgs] = None

class ChatSettings(BaseModel):
    prompt_filepath: str
    llm_args: Optional[LLMArgs] = None