from src.models import ModelDetailsConfig

from src.services.chat_rag import ChatRAG
from src.services.data_manager import DataManager
from src.services.layer1 import Layer1
from src.services.layer2 import Layer2
from src.services.layer3 import Layer3

def build_context(transcript_filepath: str):
    data_manager_obj = DataManager()
    data_manager_obj.register_model(
        model_details=ModelDetailsConfig(**{
            "model_name" : "RedHatAI/phi-4-quantized.w8a8",
            "model_base_url" : "http://192.168.1.49:9991/v1",
            "max_concurrency" : 3,
            "max_prompt_tokens_threshold" : 4096
        })
    )
    data_manager_obj.merge_transcript_chunks_by_token(
        file_path=transcript_filepath
    )
    
    layer1_obj = Layer1(data_manager_obj=data_manager_obj)
    layer1_obj.process(results_file_path="tmp/1hr_transcript_results_layer1.json")
    layer1_obj.store_in_vector_db()
    
    layer2_obj = Layer2(data_manager_obj=data_manager_obj, layer1_obj=layer1_obj)
    layer2_obj.process(results_file_path="tmp/1hr_transcript_results_layer2.json")
    layer2_obj.store_in_vector_db()
    
    layer3_obj = Layer3(data_manager_obj=data_manager_obj, layer2_obj=layer2_obj)
    layer3_obj.process(results_file_path="tmp/1hr_transcript_results_layer3.json")
    layer3_obj.store_in_vector_db()

def chat_response(user_query: str):
    chat_obj = ChatRAG()
    chat_obj.register_model(
        model_details=ModelDetailsConfig(**{
            "model_name" : "RedHatAI/phi-4-quantized.w8a8",
            "model_base_url" : "http://192.168.1.49:9991/v1",
            "max_concurrency" : 3,
            "max_prompt_tokens_threshold" : 4096
        })        
    )
    print(chat_obj.chat_query(user_query=user_query))

def main():
    chat_response(user_query="How are you?")
    # build_context("tmp/1hr_transcript.txt")

if __name__ == "__main__":
    main()