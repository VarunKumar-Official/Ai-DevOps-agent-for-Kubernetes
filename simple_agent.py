import os
import subprocess
from typing import Dict

class SimpleDevOpsAgent:
    def __init__(self):
        self.commands = {
            'pods': 'kubectl get pods -A',
            'nodes': 'kubectl get nodes',
            'services': 'kubectl get svc -A',
            'deployments': 'kubectl get deployments -A',
            'docker': 'docker ps',
            'docker-images': 'docker images',
        }

    def execute_command(self, cmd: str) -> str:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error: {e}"

    def process_query(self, query: str) -> str:
        query_lower = query.lower()
        if 'pod' in query_lower:
            if 'log' in query_lower:
                words = query.split()
                if len(words) > 3:
                    return self.execute_command(f"kubectl logs {words[-1]}")
                return "Please specify pod name: 'logs of pod <pod-name>'"
            elif 'describe' in query_lower:
                words = query.split()
                if len(words) > 2:
                    return self.execute_command(f"kubectl describe pod {words[-1]}")
                return "Please specify pod name"
            return self.execute_command(self.commands['pods'])
        elif 'node' in query_lower:
            return self.execute_command(self.commands['nodes'])
        elif 'service' in query_lower:
            return self.execute_command(self.commands['services'])
        elif 'deployment' in query_lower:
            return self.execute_command(self.commands['deployments'])
        elif 'docker' in query_lower:
            if 'image' in query_lower:
                return self.execute_command(self.commands['docker-images'])
            return self.execute_command(self.commands['docker'])
        elif 'help' in query_lower:
            return """Available commands:
  - Check pods / Show pods
  - Check nodes
  - Check services / deployments
  - Show docker containers / images
  - Logs of pod <pod-name>
  - Describe pod <pod-name>"""
        return "I can help with: pods, nodes, services, deployments, docker. Type 'help' for commands."

    def run_interactive(self):
        print("\n🤖 DevOps AI Agent (Simple Mode)")
        print("=" * 50)
        print("No LLM needed - Direct kubectl/docker access!")
        print("Type 'help' for commands, 'exit' to quit\n")
        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                if not query:
                    continue
                print("\nAgent:")
                print(self.process_query(query), "\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

if __name__ == "__main__":
    SimpleDevOpsAgent().run_interactive()
