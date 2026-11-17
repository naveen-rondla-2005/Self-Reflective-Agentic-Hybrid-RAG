import os
from typing import List, Dict
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from core.config import Config
from core.parser import TransitDocumentProcessor

class HybridTransitRetriever:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL_NAME)
        self.processor = TransitDocumentProcessor()
        self.vector_store = None
        self.bm25_retriever = None

    def initialize(self):
        if os.path.exists(Config.CHROMA_PERSIST_DIR) and os.listdir(Config.CHROMA_PERSIST_DIR):
            self.vector_store = Chroma(
                persist_directory=Config.CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings
            )
            chunks = self.processor.process_directory(Config.DOCS_DIR)
            if chunks:
                self.bm25_retriever = BM25Retriever.from_documents(chunks)
                self.bm25_retriever.k = Config.TOP_K
        else:
            self.reindex_corpus()

    def reindex_corpus(self):
        chunks = self.processor.process_directory(Config.DOCS_DIR)
        if not chunks:
            print("No documents found in directory to index.")
            return

        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=Config.CHROMA_PERSIST_DIR
        )
        self.bm25_retriever = BM25Retriever.from_documents(chunks)
        self.bm25_retriever.k = Config.TOP_K

    def retrieve(self, query: str) -> List[Document]:
        if not self.vector_store or not self.bm25_retriever:
            self.initialize()

        if not self.vector_store or not self.bm25_retriever:
            return []

        vector_docs = self.vector_store.similarity_search(query, k=Config.TOP_K)
        bm25_docs = self.bm25_retriever.invoke(query)

        rrf_constant = 60
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, doc in enumerate(vector_docs):
            key = doc.page_content[:150]
            doc_map[key] = doc
            doc_scores[key] = doc_scores.get(key, 0.0) + (1.0 / (rrf_constant + rank + 1))

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content[:150]
            doc_map[key] = doc
            doc_scores[key] = doc_scores.get(key, 0.0) + (1.0 / (rrf_constant + rank + 1))

        sorted_keys = sorted(doc_scores.keys(), key=lambda k: doc_scores[k], reverse=True)
        return [doc_map[k] for k in sorted_keys[:Config.TOP_K]]