from src.models import ModelDetailsConfig

from src.services.data_manager import DataManager
from src.services.layer1 import Layer1
from src.services.layer2 import Layer2
from src.services.layer3 import Layer3

def build_context(transcript_filepath: str):
    data_manager_obj = DataManager()
    data_manager_obj.register_model(
        model_details=ModelDetailsConfig(**{
            "model_name" : "RedHatAI/phi-4-quantized.w8a8",
            "model_base_url" : "http://10.10.10.11:9991/v1",
            "max_concurrency" : 14,
            "max_prompt_tokens_threshold" : 4096
        })
    )
    data_manager_obj.merge_transcript_chunks_by_token(
        file_path=transcript_filepath
    )
    
    layer1_obj = Layer1(data_manager_obj=data_manager_obj)
    layer1_obj.process()
    layer1_obj.store_in_vector_db()
    
    layer2_obj = Layer2(data_manager_obj=data_manager_obj, layer1_obj=layer1_obj)
    layer2_obj.process()
    layer2_obj.store_in_vector_db()
    
    # layer3_obj = Layer3(data_manager_obj=data_manager_obj, layer2_obj=layer2_obj)
    # layer3_obj.process()
    # layer3_obj.store_in_vector_db()

def main():
    # build_context("tmp/1hr_transcript.txt")
    # build_context("tmp/2hr_transcript.txt")
    build_context("tmp/Day 1 - NorthAmerica_Lean_Lab_Jul08_transcript.txt")
    build_context("tmp/Day-08 Lean_lab_20251119162712_transcript.txt")
    build_context("tmp/LeanLab-Mockups-20240910_transcript.txt")
if __name__ == "__main__":
    main()