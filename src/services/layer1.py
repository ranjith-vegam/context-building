from src.config import get_config
from log_manager import get_logger
from llm_wrapper import llm_chat

class Layer1:
    def __init__(self) -> None:
        self.logger = get_logger("layer_1_logger")
        self.layer1_settings = get_config().layer1
        
        self.max_prompt_limit = 4096
        self.model_name = ""
        self.model_base_url = ""
    