from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer

from rag_pipeline.config import EMBED_MODEL, EMBED_DEVICE, CLASSIFIER_MODEL


class FinLangEmbeddingFunction(EmbeddingFunction):
    _instance = None

    def __new__(cls, model_name: str = EMBED_MODEL, device: str = EMBED_DEVICE):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            print(f"Loading embedding model '{model_name}'...")
            cls._instance.model = SentenceTransformer(model_name, device=device)
            cls._instance.model_name = model_name
        return cls._instance

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(
            list(input),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


_classifier_pipeline = None

def get_classifier():
    global _classifier_pipeline
    if _classifier_pipeline is None:
        from transformers import pipeline
        print(f"Loading classifier '{CLASSIFIER_MODEL}'...")
        _classifier_pipeline = pipeline(
            "zero-shot-classification",
            model=CLASSIFIER_MODEL,
        )
    return _classifier_pipeline
