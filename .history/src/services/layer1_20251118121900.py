import json
import numpy as np
from log_manager import get_logger
from src.config import get_config
from llm_wrapper import llm_chat

from src.services.data_manager import DataManager
from src.database.milvus_provider import vector_store_obj

from src.utils import (
    read_prompt_file,
    get_batched_token_estimation,
    
    get_uuid,
    
    embedder_obj
)

class Layer1:
    def __init__(self, data_manager_obj: DataManager) -> None:
        self.logger = get_logger("layer1_logger")
        self.layer1_settings = get_config().layer1
        self.milvus_settings = get_config().milvus
        
        self.layer1_prompt = None
        self.results = []
        
        self.data_manager_obj = data_manager_obj
        
        self.output_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "simple_summary",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "The full LLM-generated summary text."
                        }
                    },
                    "required": ["summary"],
                    "additionalProperties": False
                }
            }
        }
        
    
    def process(self, results_file_path: str):
        try:
            if not self.layer1_prompt:
                self.layer1_prompt = read_prompt_file(
                    prompt_filepath=self.layer1_settings.prompt_filepath
                )
            
            self.layer1_settings.llm_args.response_format = self.output_schema
            
            previous_chunk_summary = ""
            for idx, trans_chunk in enumerate(self.data_manager_obj.merged_transcript_chunks):
                messages = [
                    {
                        "role" : "user",
                        "content" : self.layer1_prompt.format(
                            S_prev=previous_chunk_summary,
                            C_curr=trans_chunk
                        )
                    }                   
                ]
            
                # Calling LLM
                llm_results  = llm_chat(
                    base_url=self.data_manager_obj.model_details.model_base_url,
                    model_name=self.data_manager_obj.model_details.model_name,
                    messages_list=messages,
                    max_concurrency=self.data_manager_obj.model_details.max_concurrency,
                    args=self.layer1_settings.llm_args.model_dump(exclude_none=True),
                    logger=self.logger
                )
                previous_chunk_summary = json.loads(llm_results[0].response)["summary"]
                self.results.append({
                    "transcript_chunk" : trans_chunk,
                    "summary" : previous_chunk_summary,
                    "summary_tokens" : get_batched_token_estimation(
                        texts=[previous_chunk_summary], 
                        model_name=self.data_manager_obj.model_details.model_name
                    )[0]
                })
            
            with open(results_file_path, "w") as f:
                json.dump(self.results, f, indent=4)
            
        except Exception as e:
            self.logger.error(f"Couldn't process layer-1: {str(e)}")
            raise e
    
    def store_in_vector_db(self):
        try:
            layer1_docs = []
                
            vectors = embedder_obj.embed(
                texts=[res["summary"] for res in self.results]
            )

            print(vectors["dense_vecs"][0], type(vectors["dense_vecs"][0]))
            
            for idx, res in enumerate(self.results):
                layer1_docs.append(
                    {
                        "id" : get_uuid(),
                        "file_id" : self.data_manager_obj.file_id,
                        "dense_vector" : np.asarray(vectors["dense_vecs"][idx], dtype=np.float32),
                        "sparse_vector" : vectors["lexical_weights"][idx],
                        "metadata" : res
                    }
                )
            
            print(f"LLM output: {len(self.results)}, milvus: {len(layer1_docs)}")
            vector_store_obj.create_or_upsert_collection(
                collection_name=self.milvus_settings.collection_name,
                partition_name="layer_1",
                documents=layer1_docs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store the layer-1 results in vector DB: {str(e)}")