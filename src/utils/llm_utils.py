from transformers import AutoTokenizer

def get_batched_token_estimation(texts: list[str], model_name: str):
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokens = tokenizer(texts, padding=False, truncation=False)
        token_counts = [len(ids) for ids in tokens['input_ids']]
        return token_counts
    
    except Exception as e:
        print(f"[ERROR] Failed to get token count for model '{model_name}': {e}")
        raise e

# For reading txt file
def read_txt_file(filepath: str):
    """
    Reads a TXT file and returns its content.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filepath}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to read file {filepath}: {e}")
        return []

# Reads prompt txt files
def read_prompt_file(prompt_filepath: str):
    return read_txt_file(filepath=prompt_filepath)