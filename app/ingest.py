import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.tools.policy_search import get_chroma_collection

def ingest_policies() -> None:
    policies_dir = os.path.join('data', 'policies')
    if not os.path.exists(policies_dir):
        return
    collection = get_chroma_collection()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=250, separators=['\n\n', '\n', ' ', ''])
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []
    ids: list[str] = []
    for filename in os.listdir(policies_dir):
        if not filename.endswith('.pdf'):
            continue
        filepath = os.path.join(policies_dir, filename)
        reader = PdfReader(filepath)
        pages_text: list[str] = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pages_text.append(extracted)
        text = '\n'.join(pages_text)
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({'source_file': filename, 'chunk_index': i})
            ids.append(f'{filename}_{i}')
    if documents:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
if __name__ == '__main__':
    ingest_policies()