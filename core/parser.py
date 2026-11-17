import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from core.config import Config

class TransitDocumentProcessor:
    def __init__(self, chunk_size: int = Config.CHUNK_SIZE, chunk_overlap: int = Config.CHUNK_OVERLAP):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            add_start_index=True
        )

    def load_pdf(self, file_path: str) -> List[Document]:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_name"] = os.path.basename(file_path)
            doc.page_content = " ".join(doc.page_content.split())
        return docs

    def process_directory(self, directory_path: str) -> List[Document]:
        all_chunks = []
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            return all_chunks

        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    docs = self.load_pdf(pdf_path)
                    chunks = self.splitter.split_documents(docs)
                    all_chunks.extend(chunks)
        return all_chunks