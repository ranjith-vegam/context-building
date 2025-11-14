from pydantic import BaseModel


class ModelDetailsConfig(BaseModel):
    """
    Pydantic for validating Model Details from AI-Engine Register Model
    """
    
    model_name: str
    model_base_url: str
    max_concurrency: int
    max_prompt_tokens_threshold: int