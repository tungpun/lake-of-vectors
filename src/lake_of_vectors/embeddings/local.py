from sentence_transformers import SentenceTransformer


class LocalEmbedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self._model_name = model
        self._model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def model_name(self) -> str:
        return f"local:{self._model_name}"
