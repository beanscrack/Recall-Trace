"""embed(texts) -> vectors, via Voyage AI."""
from functools import lru_cache

import voyageai

from . import config


@lru_cache
def _client() -> voyageai.Client:
    if not config.VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY is not set")
    return voyageai.Client(api_key=config.VOYAGE_API_KEY)


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """input_type is 'document' for stored text, 'query' for search queries."""
    res = _client().embed(texts, model=config.EMBEDDING_MODEL, input_type=input_type,
                          output_dimension=config.EMBEDDING_DIM)
    return res.embeddings


def embed_query(text: str) -> list[float]:
    return embed([text], input_type="query")[0]
