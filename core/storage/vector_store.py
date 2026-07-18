from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from core.config import CHROMA_PERSIST_DIR,EMBEDDING_MODEL

_embeddings=None
_store=None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings

def get_store()->Chroma:
    global _store
    if _store is None:
        _store=Chroma(
            collection_name="memories",
            embedding_function=get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR
        )
    return _store


def add_memory(memory_id:str,content:str,user_id:str,type_:str)->None:
    store=get_store()
    store.add_texts(
        texts=[content],
        metadatas=[{"user_id":user_id,"type":type_}],
        ids=[memory_id],
    )

def query_similar(query:str,user_id:str,k:int=5):
    store=get_store()
    results=store.similarity_search_with_score(
        query,k=k,filter={"user_id":user_id}
    )
    return [
        {"id":doc.id,"content":doc.page_content,"metadata":doc.metadata,"distance":score}
        for doc,score in results
    ]

