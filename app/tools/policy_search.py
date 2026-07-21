import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
_CHROMA_CLIENT = None
_EMBEDDING_FUNCTION: SentenceTransformerEmbeddingFunction | None = None

def get_chroma_collection() -> chromadb.Collection:
    global _CHROMA_CLIENT, _EMBEDDING_FUNCTION
    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.PersistentClient(path='chroma_db')
        _EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
    return _CHROMA_CLIENT.get_or_create_collection(name='policies', embedding_function=_EMBEDDING_FUNCTION)
