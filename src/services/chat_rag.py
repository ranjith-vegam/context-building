import json
import numpy as np

from log_manager import get_logger
from llm_wrapper import llm_chat

from src.models import ModelDetailsConfig
from src.config import get_config
from src.database.milvus_provider import vector_store_obj
from src.utils import (
    read_prompt_file,
    embedder_obj
)

class ChatRAG():
    def __init__(self) -> None:
        self.milvus_settings = get_config().milvus
        self.chat_settings = get_config().chat
        self.logger = get_logger("chat_rag_logger")

        self.chat_prompt = None

        self.output_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "context_bound_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "The LLM-generated answer strictly based on the provided meeting context. No external knowledge or references."
                        }
                    },
                    "required": ["response"],
                    "additionalProperties": False
                }
            }
        }

    def register_model(self, model_details: ModelDetailsConfig):
        try:
            self.model_details = model_details
        except Exception as e:
            self.logger.error(f"Couldn't register model: {str(e)}")        

    def get_query_embedding(self, user_query: str):
        try:
            vectors = embedder_obj.embed(
                texts=[user_query]
            )            
            return {
                "dense_vector" : np.asarray(vectors["dense_vecs"][0], dtype=np.float32),
                "sparse_vector" : vectors["lexical_weights"][0],                
            }
        except Exception as e:
            self.logger.error(f"Failed get embedding for user query: {str(e)}")

    def chat_query(self, user_query: str):
        try:
            vector = self.get_query_embedding(user_query=user_query)

            layer1_context = self.layer_1_retrieval(vector=vector)
            file_ids = []
            for idx, cntx in enumerate(layer1_context):
                file_ids.append(cntx["file_id"])
                layer1_context[idx]["layer"] = 1
            
            layer2_context = self.layer_2_retrieval(
                vector=vector, 
                filters={
                    "file_id" : file_ids
                }
            )
            
            context = ""
            for idx, cntx in enumerate(layer2_context):
                metadata = cntx["metadata"]
                context += f"{metadata["topic"]}\n{metadata["content"]}\n\n"
                layer2_context[idx]["layer"] = 2
            
            if not self.chat_prompt:
                self.chat_prompt = read_prompt_file(
                    prompt_filepath=self.chat_settings.prompt_filepath
                )

            self.chat_settings.llm_args.response_format = self.output_schema

            messages = [{
                "role" : "user",
                "content" : self.chat_prompt.format(
                    retrieved_context=context,
                    user_query=user_query
                )
            }]

            # Calling LLM
            llm_results  = llm_chat(
                base_url=self.model_details.model_base_url,
                model_name=self.model_details.model_name,
                messages_list=messages,
                max_concurrency=self.model_details.max_concurrency,
                args=self.chat_settings.llm_args.model_dump(exclude_none=True),
                logger=self.logger
            )

            resp = llm_results[0]
            return {
                "response" : json.loads(resp.response)["response"],
                "citations" : layer1_context + layer2_context
            }

        except Exception as e:
            self.logger.error(f"Failed to answer the user query-{user_query} : {str(e)}")
            return {
                "response" : "Something went wrong, Try again",
                "citations" : []
            }            

    def layer_1_retrieval(self, vector: dict):
        try:
            retrieved_context = vector_store_obj.hybrid_search(
                collection_name=self.milvus_settings.collection_name,
                dense_vector=vector["dense_vector"],
                sparse_vector=vector['sparse_vector'],
                partition_names=[self.milvus_settings.partition_layer1],
                top_K=3
            )
            return retrieved_context
        except Exception as e:
            self.logger.error(f"Failed in Layer-1 retrieval: {str(e)}")


    def layer_2_retrieval(self, vector: dict, filters: dict):
        try:
            retrieved_context = vector_store_obj.hybrid_search(
                collection_name=self.milvus_settings.collection_name,
                dense_vector=vector["dense_vector"],
                sparse_vector=vector['sparse_vector'],
                partition_names=[self.milvus_settings.partition_layer2],
                top_K=3,
                filters=filters
            )
            return retrieved_context
        except Exception as e:
            self.logger.error(f"Failed in Layer-2 retrieval: {str(e)}")

chat_obj = ChatRAG()
chat_obj.register_model(
    model_details=ModelDetailsConfig(**{
        "model_name" : "RedHatAI/phi-4-quantized.w8a8",
        "model_base_url" : "http://192.168.1.49:9991/v1",
        "max_concurrency" : 3,
        "max_prompt_tokens_threshold" : 4096
    })        
)                     