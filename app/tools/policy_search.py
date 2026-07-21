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

def policy_search(query: str, k: int=4) -> list[str] | str:
    collection = get_chroma_collection()
    results = collection.query(query_texts=[query], n_results=k, include=['documents', 'distances'])
    if not results['documents'] or not results['documents'][0]:
        return 'no relevant policy content found'
    distances = results['distances'][0] if results['distances'] else []
    documents = results['documents'][0]
    relevance_threshold = 1.5
    valid_chunks: list[str] = []
    for doc, dist in zip(documents, distances):
        if dist < relevance_threshold:
            valid_chunks.append(doc)
    if not valid_chunks:
        return 'no relevant policy content found'
    return valid_chunks