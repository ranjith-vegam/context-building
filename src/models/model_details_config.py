from pydantic import BaseModel


class ModelDetailsConfig(BaseModel):
    """
    Pydantic for validating Model Details from AI-Engine Register Model
    """
    
    model_name: str
    model_base_url: str
    max_concurrency: int
    max_prompt_tokens_threshold: int

# Request model
class ChatRequest(BaseModel):
    message: str
    top_k_layer_1: int
    top_k_layer_2: int
    top_k_layer_3: int
    collection_name: str


# Response model
class ChatResponse(BaseModel):
    response: str
    citations: list[dict]    