from typing import List
from sentence_transformers import CrossEncoder


class LocalReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = "cpu"):
        self.model = CrossEncoder(model_name, device=device)

    def score(
        self, query: str, passages: List[str], batch_size: int = 16
    ) -> List[float]:
        pairs = [(query, p) for p in passages]
        scores = self.model.predict(
            pairs, batch_size=batch_size, show_progress_bar=False
        )
        return [float(s) for s in scores]
