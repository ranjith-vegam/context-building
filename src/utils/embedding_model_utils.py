# type: ignore
from FlagEmbedding import BGEM3FlagModel
from typing import Any
import threading


class Embedder:
    """
    Wrapper class around BGE-M3 model
    ensuring a single shared instance is used for all embedding calls.
    """

    _model_instance = None
    _lock = threading.Lock()

    def __init__(self, device: str = "cuda", use_fp16: bool = True):
        """
        Initialize the embedder (loads model only once).
        """
        with Embedder._lock:
            if Embedder._model_instance is None:
                print("Loading BGE-M3 model...")

                Embedder._model_instance = BGEM3FlagModel(
                    "BAAI/bge-m3",
                    use_fp16=use_fp16,
                    device=device
                )

        self.model = Embedder._model_instance

    def embed(self, texts: list[str]) -> dict[str, Any]:
        """
        Generate embeddings for a list of texts.
        Returns: {"dense": [...], "sparse": [...], "colbert": [...]}
        """
        return self.model.encode(
            sentences=texts,
            return_dense=True,
            return_sparse=True,
        )

embedder_obj = Embedder()