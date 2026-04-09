import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
from typing import Dict, List
from tools import kubectl_tool, docker_tool, log_analyzer
from rag_system import RAGSystem

load_dotenv()

class DevOpsAgent:
    def __init__(self, model: str = "gemini-1.5-flash-latest"):
        self.model = model
        self.rag = RAGSystem()
        self.conversation_history = []
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your-gemini-api-key-here':
            print("⚠️  GEMINI_API_KEY not set. Get free key at: https://makersuite.google.com/app/apikey")
        else:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)

    def initialize_rag(self):
        print("Loading knowledge base...")
        self.rag.load_documents()

    def get_llm_response(self, prompt: str, context: str = "") -> str:
        if not os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY') == 'your-gemini-api-key-here':
            return "⚠️ Gemini API key not configured.\nGet FREE key at: https://makersuite.google.com/app/apikey\nThen add to .env: GEMINI_API_KEY=your-key"
        full_prompt = f"Context:\n{context}\n\nQuery: {prompt}" if context else prompt
        try:
            response = self.client.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini: {e}"

    def execute_tool(self, tool: str, args: List[str]) -> Dict:
        if tool == "kubectl":
            return kubectl_tool.execute_kubectl(args)
        elif tool == "docker":
            return docker_tool.execute_docker(args)
        return {"error": f"Unknown tool: {tool}"}

    def process_query(self, query: str) -> str:
        query_lower = query.lower()
        if "analyze log" in query_lower or ("why is" in query_lower and "crash" in query_lower):
            context = self.rag.get_context(query)
            return self.get_llm_response(log_analyzer.get_analysis_prompt(query), context)
        if "kubectl" in query_lower or "pod" in query_lower or "deployment" in query_lower:
            context = self.rag.get_context(query)
            return self.get_llm_response(f"Suggest the appropriate kubectl command for: {query}", context)
        if "docker" in query_lower or "container" in query_lower:
            context = self.rag.get_context(query)
            return self.get_llm_response(f"Suggest the appropriate docker command for: {query}", context)
        context = self.rag.get_context(query)
        return self.get_llm_response(query, context)

    def run_interactive(self):
        print("DevOps AI Agent initialized\nType 'exit' to quit\n")
        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                if not query:
                    continue
                print("\nAgent: ", end="")
                print(self.process_query(query), "\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

def main():
    agent = DevOpsAgent()
    agent.initialize_rag()
    agent.run_interactive()

if __name__ == "__main__":
    main()
