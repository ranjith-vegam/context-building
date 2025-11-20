import json

from log_manager import get_logger

from src.utils import (
    get_batched_token_estimation,
    get_ulid
)

from src.models import (
    ModelDetailsConfig
)

class DataManager:
    def __init__(self) -> None:
        self.logger = get_logger("data_manager")
        
        self.model_details: ModelDetailsConfig = None
        self.transcript_json = None
    
        self.merged_transcript_chunks = []
        
        self.file_id = get_ulid()
        self.file_path: str = None
        
    def register_model(self, model_details: ModelDetailsConfig):
        try:
            self.model_details = model_details
        except Exception as e:
            self.logger.error(f"Couldn't register model: {str(e)}")
    
    def _load_transcript(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                text_data = f.read()

            self.transcript_json = json.loads(json.loads(text_data))
            trans_chunks = [trans_segment["text"] for trans_segment in self.transcript_json]
            token_counts = get_batched_token_estimation(
                texts = trans_chunks,
                model_name=self.model_details.model_name
            )
            
            for idx, token_count in enumerate(token_counts):
                self.transcript_json[idx]["token_count"] = token_count
                    
        except Exception as e:
            self.logger.error(f"Couldn't load transcript from txt file-{file_path} : {str(e)}")
            
    def merge_transcript_chunks_by_token(self, file_path: str):                
        try:
            self.file_path = file_path
            self._load_transcript(file_path=file_path)
            
            # Merge segments until threshold
            buffer_texts = []
            buffer_tokens = 0

            for seg in self.transcript_json:
                seg_text = seg["text"]
                seg_tokens = seg.get("token_count", 0)

                buffer_texts.append(seg_text)
                buffer_tokens += seg_tokens

                if buffer_tokens >= self.model_details.max_prompt_tokens_threshold:
                    # Join all buffered texts
                    self.merged_transcript_chunks.append(" ".join(buffer_texts))
                    # Reset buffer
                    buffer_texts = []
                    buffer_tokens = 0

            # Add remaining buffer if any
            if buffer_texts:
                self.merged_transcript_chunks.append(" ".join(buffer_texts))
            
            self.logger.info(f"Merged transcript chunks according to model's prompt tokens threshold - {len(self.merged_transcript_chunks)} chunks")
            return self.merged_transcript_chunks
        
        except Exception as e:
            self.logger.error(f"Not able to merge transcript chunks according to threshold: {str(e)}")
            raise e            
            
    