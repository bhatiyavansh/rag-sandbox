import faiss
import numpy as np

class VectorStore:
    def __init__(self, dim):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)  # L2 distance
        self.texts = []  # store original text chunks

    def add(self, text_chunks: list, embeddings: list):
        vectors = np.array(embeddings, dtype=np.float32)
        self.index.add(vectors)
        self.texts.extend(text_chunks)

    def search(self, query_embedding, top_k=5):
        D, I = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
        results = [self.texts[i] for i in I[0] if i < len(self.texts)]
        return results
