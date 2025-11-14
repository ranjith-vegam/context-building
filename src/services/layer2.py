import json
from log_manager import get_logger
from src.config import get_config
from llm_wrapper import llm_chat

from src.services.data_manager import DataManager
from src.services.layer1 import Layer1

from src.utils import (
    read_prompt_file,
    get_batched_token_estimation
)

class Layer2:
    def __init__(
        self, 
        data_manager_obj: DataManager,
        layer1_obj: Layer1) -> None:
        
        self.logger = get_logger("layer2_logger")
        self.layer2_settings = get_config().layer2
        self.layer2_prompt = None
        self.results = []
        
        self.layer1_obj = layer1_obj
        
        self.data_manager_obj = data_manager_obj
        
        self.output_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "topic_extraction",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Short, specific, content-based topic title extracted from the raw transcript chunk."
                            },
                            "summary": {
                                "type": "string",
                                "description": "A detailed, self-contained summary of the topic including key points, decisions, reasoning, action items, constraints, relationships, and unresolved questions."
                            }
                        },
                        "required": ["topic", "summary"],
                        "additionalProperties": False
                    }
                }
            }
        }        
    
    def process(self, results_file_path: str):
        try:
            if not self.layer2_prompt:
                self.layer2_prompt = read_prompt_file(
                    prompt_filepath=self.layer2_settings.prompt_filepath
                )
            
            self.layer2_settings.llm_args.response_format = self.output_schema
            
            messages = []
            for idx, trans_chunk in enumerate(self.data_manager_obj.merged_transcript_chunks):
                messages.append([{
                        "role" : "user",
                        "content" : self.layer2_prompt.format(
                            S_layer1=self.layer1_obj.results[idx]["summary"],
                            C_raw=trans_chunk
                        )
                    }])
            
            # Calling LLM
            llm_results  = llm_chat(
                base_url=self.data_manager_obj.model_details.model_base_url,
                model_name=self.data_manager_obj.model_details.model_name,
                messages_list=messages,
                max_concurrency=self.data_manager_obj.model_details.max_concurrency,
                args=self.layer2_settings.llm_args.model_dump(exclude_none=True),
                logger=self.logger
            )
                
            for idx, resp in enumerate(llm_results):
                topics_arr = json.loads(resp.response)
                self.results.append(
                    {
                        "chunk-id" : f"chunk-{idx+1}",
                        "topics" : topics_arr
                    }
                )
            
            with open(results_file_path, "w") as f:
                json.dump(self.results, f, indent=4)
            
        except Exception as e:
            self.logger.error(f"Couldn't process layer-2: {str(e)}")
            raise e
