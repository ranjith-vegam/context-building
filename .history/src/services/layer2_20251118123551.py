import json
import numpy as np
from log_manager import get_logger
from src.config import get_config
from llm_wrapper import llm_chat

from src.services.data_manager import DataManager
from src.services.layer1 import Layer1

from src.database.milvus_provider import vector_store_obj

from src.utils import (
    read_prompt_file,
    get_batched_token_estimation,
    
    get_uuid,
    
    embedder_obj
)

class Layer2:
    def __init__(
        self, 
        data_manager_obj: DataManager,
        layer1_obj: Layer1) -> None:
        
        self.logger = get_logger("layer2_logger")
        self.layer2_settings = get_config().layer2
        self.milvus_settings = get_config().milvus
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
                            "content": {
                                "type": "string",
                                "description": "A detailed, self-contained summary of the topic including key points, decisions, reasoning, action items, constraints, relationships, and unresolved questions."
                            }
                        },
                        "required": ["topic", "content"],
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
        
    def store_in_vector_db(self):
        try:
            c = 0
            layer2_docs = []
            for res in self.results:
                vectors = embedder_obj.embed(
                    texts=[f"Topic: {elem['topic']}\nContent: {elem['content']}" for elem in res['topics']]
                )                
                for idx, metadata in enumerate(res['topics']):
                    
                    layer2_docs.append(
                        {
                            "id" : get_uuid(),
                            "file_id" : self.data_manager_obj.file_id,
                            "dense_vector" : np.asarray(vectors["dense_vecs"][idx], dtype=np.float32),
                            "sparse_vector" : vectors["lexical_weights"][idx],
                            "metadata" : metadata
                        }
                    )
                c += len(res['topics"])
            
            print(f"LLM output: {c}, milvus: {len(layer2_docs)}")
            vector_store_obj.create_or_upsert_collection(
                collection_name=self.milvus_settings.collection_name,
                partition_name="layer_2",
                documents=layer2_docs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store the layer-2 results in vector DB: {str(e)}")        
