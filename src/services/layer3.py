import json
import numpy as np
from log_manager import get_logger
from src.config import get_config
from llm_wrapper import llm_chat

from src.services.data_manager import DataManager
from src.services.layer2 import Layer2

from src.database.milvus_provider import vector_store_obj

from src.utils import (
    read_prompt_file,
    get_batched_token_estimation,
    
    get_uuid,
    
    embedder_obj
)

class Layer3:
    def __init__(
        self, 
        data_manager_obj: DataManager,
        layer2_obj: Layer2) -> None:
        
        self.logger = get_logger("layer3_logger")
        self.layer3_settings = get_config().layer3
        self.milvus_settings = get_config().milvus
        self.layer3_prompt = None
        self.results = []
        
        self.layer2_obj = layer2_obj
        
        self.data_manager_obj = data_manager_obj
        
        self.output_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "amusextraction",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "A standalone, context-rich atomic meaning unit extracted from the transcript chunk."
                    }
                }
            }
        }
    
    def process(self, results_file_path: str):
        try:
            if not self.layer3_prompt:
                self.layer3_prompt = read_prompt_file(
                    prompt_filepath=self.layer3_settings.prompt_filepath
                )
            
            self.layer3_settings.llm_args.response_format = self.output_schema
            
            messages = []
            for idx, trans_chunk in enumerate(self.data_manager_obj.merged_transcript_chunks):
                messages.append([{
                        "role" : "user",
                        "content" : self.layer3_prompt.format(
                            layer2_topics=self.layer2_obj.results[idx]["topics"],
                            C_raw=trans_chunk
                        )
                    }])
            
            # Calling LLM
            llm_results  = llm_chat(
                base_url=self.data_manager_obj.model_details.model_base_url,
                model_name=self.data_manager_obj.model_details.model_name,
                messages_list=messages,
                max_concurrency=self.data_manager_obj.model_details.max_concurrency,
                args=self.layer3_settings.llm_args.model_dump(exclude_none=True),
                logger=self.logger
            )
                
            for idx, resp in enumerate(llm_results):
                granular_chunks = json.loads(resp.response)
                self.results.append(
                    {
                        "chunk-id" : f"chunk-{idx+1}",
                        "granular_chunks" : granular_chunks
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
            layer3_docs = []
            for res in self.results:
                vectors = embedder_obj.embed(
                    texts=[granular_chunk for granular_chunk in res["granular_chunks"]]
                )                
                for idx, granular_chunk in enumerate(res["granular_chunks"]):
                    
                    layer3_docs.append(
                        {
                            "id" : get_uuid(),
                            "file_id" : self.data_manager_obj.file_id,
                            "dense_vector" : np.asarray(vectors["dense_vecs"][idx], dtype=np.float32),
                            "sparse_vector" : vectors["lexical_weights"][idx],
                            "metadata" : {
                                "granular_chunk" : granular_chunk,
                                "file_path" : self.data_manager_obj.file_path
                            }
                        }
                    )
                c += len(res["granular_chunks"])
            
            self.logger.info(f"LLM output: {c}, milvus: {len(layer3_docs)}")
            vector_store_obj.create_or_upsert_collection(
                collection_name=self.milvus_settings.collection_name,
                partition_name=self.milvus_settings.partition_layer3,
                documents=layer3_docs
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store the layer-2 results in vector DB: {str(e)}")    