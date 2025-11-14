from src.models import ModelDetailsConfig
from src.services.data_manager import DataManager
from src.services.layer1 import Layer1
from src.services.layer2 import Layer2

def main():
    data_manager_obj = DataManager()
    data_manager_obj.register_model(
        model_details=ModelDetailsConfig(**{
            "model_name" : "RedHatAI/phi-4-quantized.w8a8",
            "model_base_url" : "http://192.168.3.196:9122/v1",
            "max_concurrency" : 3,
            "max_prompt_tokens_threshold" : 4096
        })
    )
    data_manager_obj.merge_transcript_chunks_by_token(
        file_path="tmp/1hr_transcript.txt"
    )
    
    layer1_obj = Layer1(data_manager_obj=data_manager_obj)
    layer1_obj.process(results_file_path="tmp/1hr_transcript_results_layer1.json")
    
    layer2_obj = Layer2(data_manager_obj=data_manager_obj, layer1_obj=layer1_obj)
    layer2_obj.process(results_file_path="tmp/1hr_transcript_results_layer2.json")

if __name__ == "__main__":
    main()