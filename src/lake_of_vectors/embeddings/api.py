from openai import OpenAI


class APIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        self._model_name = model
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(input=texts, model=self._model_name)
        return [item.embedding for item in response.data]

    @property
    def model_name(self) -> str:
        return f"openai:{self._model_name}"
