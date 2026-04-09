import os
import chromadb
from chromadb.config import Settings
from typing import List

class RAGSystem:
    def __init__(self, knowledge_path: str = "./knowledge"):
        self.knowledge_path = knowledge_path
        self.client = chromadb.Client(Settings(
            persist_directory="./chroma_db",
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection("devops_knowledge")

    def load_documents(self):
        """Load documents from knowledge directories"""
        docs = []
        doc_ids = []

        for root, dirs, files in os.walk(self.knowledge_path):
            for file in files:
                if file.endswith(('.yaml', '.yml', '.md', '.txt')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                            docs.append(content)
                            doc_ids.append(filepath)
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")

        if docs:
            self.collection.add(documents=docs, ids=doc_ids)
            print(f"Loaded {len(docs)} documents into RAG system")
        else:
            print("No documents found to load")

    def query(self, query_text: str, n_results: int = 3) -> List[str]:
        """Query the knowledge base"""
        results = self.collection.query(query_texts=[query_text], n_results=n_results)
        if results['documents']:
            return results['documents'][0]
        return []

    def get_context(self, query: str) -> str:
        """Get relevant context for a query"""
        docs = self.query(query)
        if docs:
            return "\n\n---\n\n".join(docs[:2])
        return ""
