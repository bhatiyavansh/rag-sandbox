import os
import openai
import numpy as np

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_embedding(text: str, model="text-embedding-3-small") -> np.ndarray:
    """Return embedding vector for a given text."""
    resp = openai.Embedding.create(input=text, model=model)
    return np.array(resp['data'][0]['embedding'], dtype=np.float32)
