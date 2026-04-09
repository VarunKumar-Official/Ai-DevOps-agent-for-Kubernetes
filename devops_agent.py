from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import subprocess
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
import threading
import time
from datetime import datetime
from auth import AuthManager, login_required
from tools.k8s_mcp_tool import K8sMCPTool
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

auth_manager = AuthManager()

# Initialize Redis cache (optional)
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6380, db=0, decode_responses=True)
    redis_client.ping()
    print("✅ Redis cache connected")
except Exception:
    redis_client = None
    print("⚠️ Redis not available (optional)")


class DevOpsAIAgent:
    def __init__(self):
        self.cluster_knowledge = self.load_cluster_knowledge()
        self.conversation_memory = []
        self.last_command = None
        self.last_output = None
        self.pod_namespace_cache = {}
        self.redis_client = redis_client

        if self.redis_client:
            try:
                cached_pods = self.redis_client.hgetall('pod_namespace_map')
                self.pod_namespace_cache = cached_pods
                print(f"✅ Loaded {len(cached_pods)} pods from Redis cache")
            except:
                pass

        # Initialize K8s MCP Tool
        try:
            self.k8s_mcp = K8sMCPTool()
            self.mcp_enabled = True
            print("✅ K8s MCP Server connected")
        except Exception as e:
            self.k8s_mcp = None
            self.mcp_enabled = False
            print(f"⚠️ K8s MCP Server not available: {e}")

        # Initialize LLM
        self.llm_enabled = False
        self.llm_type = None

        # Try Ollama first (local, free)
        try:
            import requests
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code == 200:
                self.llm_type = 'ollama'
                self.llm_enabled = True
                print("✅ Using Ollama (local, unlimited)")
        except:
            pass

        # Fallback to Gemini
        if not self.llm_enabled:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key and api_key != 'your-gemini-api-key-here':
                genai.configure(api_key=api_key)
                try:
                    self.llm = genai.GenerativeModel('gemini-2.5-flash')
                    self.llm_type = 'gemini'
                    self.llm_enabled = True
                    print("✅ Using Gemini (cloud)")
                except:
                    print("⚠️ Gemini not available")

        # Initialize RAG system
        try:
            self.rag_client = chromadb.Client(Settings(
                persist_directory="./chroma_db",
                anonymized_telemetry=False
            ))
            self.rag_collection = self.rag_client.get_or_create_collection("devops_knowledge")
            self.load_knowledge_base()
        except Exception as e:
            print(f"⚠️ RAG system initialization failed: {e}")
            self.rag_collection = None

    def load_cluster_knowledge(self):
        """Load cluster knowledge - customize this for your environment"""
        return {
            'nodes': {
                'master-node-01': {'role': 'control-plane', 'status': 'Ready', 'ip': '10.0.0.10'},
                'worker-node-01': {'role': 'worker', 'status': 'Ready', 'ip': '10.0.0.11'},
                'worker-node-02': {'role': 'worker', 'status': 'Ready', 'ip': '10.0.0.12'},
                'worker-node-03': {'role': 'worker', 'status': 'Ready', 'ip': '10.0.0.13'}
            },
            'known_issues': {
                'ImagePullBackOff': {
                    'description': 'Registry authentication failure',
                    'fix': 'Create docker-registry secret with registry credentials'
                },
                'NodeNotReady': {
                    'description': 'Kubelet stopped on worker node',
                    'fix': 'SSH to node and restart kubelet: sudo systemctl restart kubelet'
                },
                'PodPending': {
                    'description': 'Scheduling failure due to node unavailability or anti-affinity',
                    'fix': 'Fix NotReady nodes or adjust pod anti-affinity rules'
                },
                'MetricsMissing': {
                    'description': 'HPA cannot get metrics',
                    'fix': 'Install metrics-server in kube-system namespace'
                },
                'LoadBalancerPending': {
                    'description': 'No external LB provider',
                    'fix': 'Install MetalLB for on-premise load balancing'
                }
            },
            'namespaces': ['default', 'kube-system', 'monitoring', 'ingress-nginx']
        }

    def load_knowledge_base(self):
        if not self.rag_collection:
            return
        docs = []
        doc_ids = []
        cluster_doc = f"""Kubernetes Cluster Configuration:
Nodes: {', '.join(self.cluster_knowledge['nodes'].keys())}
Namespaces: {', '.join(self.cluster_knowledge['namespaces'])}
Known Issues: {', '.join(self.cluster_knowledge['known_issues'].keys())}
"""
        docs.append(cluster_doc)
        doc_ids.append("cluster_config")

        knowledge_path = "./knowledge"
        if os.path.exists(knowledge_path):
            for root, dirs, files in os.walk(knowledge_path):
                for file in files:
                    if file.endswith(('.yaml', '.yml', '.md', '.txt')):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r') as f:
                                docs.append(f.read())
                                doc_ids.append(filepath)
                        except Exception as e:
                            print(f"Error reading {filepath}: {e}")
        if docs:
            try:
                self.rag_collection.add(documents=docs, ids=doc_ids)
                print(f"✅ Loaded {len(docs)} documents into RAG system")
            except Exception as e:
                print(f"⚠️ Error loading documents: {e}")

    def get_rag_context(self, query: str) -> str:
        if not self.rag_collection:
            return ""
        try:
            results = self.rag_collection.query(query_texts=[query], n_results=2)
            if results['documents']:
                return "\n\n---\n\n".join(results['documents'][0])
        except Exception as e:
            print(f"RAG query error: {e}")
        return ""

    def ask_llm(self, prompt: str, context: str = "") -> str:
        if not self.llm_enabled:
            return "⚠️ LLM not available. Using rule-based response."
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{prompt}"
        if self.conversation_memory:
            memory_context = "\n".join([
                f"User: {m.get('query', m.get('command', 'N/A'))}\nAgent: {str(m.get('response', ''))[:200]}"
                for m in self.conversation_memory[-3:] if m.get('query') or m.get('command')
            ])
            if memory_context:
                full_prompt = f"Previous conversation:\n{memory_context}\n\n{full_prompt}"
        try:
            if self.llm_type == 'ollama':
                import requests
                response = requests.post('http://localhost:11434/api/generate',
                    json={'model': 'llama3.2', 'prompt': full_prompt, 'stream': False}, timeout=30)
                return response.json()['response']
            else:
                response = self.llm.generate_content(full_prompt)
                return response.text
        except Exception as e:
            return f"LLM Error: {e}"

    def analyze_with_llm(self, query: str) -> dict:
        if not self.llm_enabled:
            return {'use_llm': False}
        context = self.get_rag_context(query)
        prompt = f"""Analyze this DevOps query and respond in JSON format:
{{
  "intent": "kubectl_command|log_analysis|troubleshooting|general_question",
  "needs_kubectl": true/false,
  "suggested_command": "command here or null",
  "explanation": "brief explanation"
}}

Query: {query}

If it's a kubectl/docker command, extract it. If it's troubleshooting, set intent accordingly."""
        try:
            response = self.ask_llm(prompt, context)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            analysis = json.loads(response)
            analysis['use_llm'] = True
            return analysis
        except Exception:
            return {'use_llm': False}

    def get_cluster_recommendations(self) -> str:
        return """🎯 **Cluster Recommendations & Improvements**

**Recommended Additions:**

✅ **1. Monitoring Stack**
   - Prometheus + Grafana for metrics visualization
   - AlertManager for proactive alerts
   Commands:
   • helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   • helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

✅ **2. Logging Stack**
   - ELK/EFK stack for centralized logging
   - Filebeat or Fluentd for log collection

✅ **3. Backup Solution**
   - Velero for cluster backups
   Commands:
   • velero install --provider aws --bucket k8s-backups
   • velero schedule create daily --schedule="0 2 * * *"

✅ **4. Service Mesh (Optional)**
   - Istio or Linkerd for mTLS, traffic management, observability

✅ **5. GitOps - ArgoCD/FluxCD**
   - Automate deployments from Git
   Command: kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

✅ **6. Policy Engine - OPA/Kyverno**
   - Enforce security policies

✅ **7. Security Scanning**
   - Trivy for image scanning
   - Falco for runtime security

Type 'help' for all available commands!"""

    def analyze_output_and_suggest(self, command: str, output: str) -> str:
        suggestions = []
        if 'error' in output.lower() or 'failed' in output.lower():
            suggestions.append("\n\n🔍 **Error Detected!**")
            if 'imagepullbackoff' in output.lower():
                suggestions.append("**Issue:** ImagePullBackOff - Cannot pull container image")
                suggestions.append("**Fix:** Check image name, verify registry credentials")
            elif 'crashloopbackoff' in output.lower():
                suggestions.append("**Issue:** CrashLoopBackOff - Pod keeps crashing")
                suggestions.append("**Fix:** Check logs with: kubectl logs <pod> -n <ns> --previous")
            elif 'pending' in output.lower():
                suggestions.append("**Issue:** Pod Pending - Cannot be scheduled")
                suggestions.append("**Fix:** Check node status and resource requests")
            elif 'oomkilled' in output.lower():
                suggestions.append("**Issue:** OOMKilled - Out of memory")
                suggestions.append("**Fix:** Increase memory limit in deployment")
        elif 'running' in output.lower() and 'kubectl get pods' in command.lower():
            running_count = output.lower().count('running')
            if running_count > 0:
                suggestions.append(f"\n\n✅ **{running_count} pods running successfully**")
        return "\n".join(suggestions) if suggestions else ""

    def execute_command(self, cmd: str, username: str = None) -> str:
        try:
            env = os.environ.copy()
            namespace = None
            if username:
                kubeconfig_path = auth_manager.get_user_kubeconfig(username)
                if kubeconfig_path:
                    env['KUBECONFIG'] = kubeconfig_path
                    namespace = self.get_user_namespace(username)
                    if namespace and namespace != 'default':
                        if 'kubectl get pods -A' in cmd or 'kubectl get pods --all-namespaces' in cmd:
                            cmd = cmd.replace('kubectl get pods -A', f'kubectl get pods -n {namespace}')
                            cmd = cmd.replace('kubectl get pods --all-namespaces', f'kubectl get pods -n {namespace}')

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, env=env)
            output = result.stdout if result.returncode == 0 else result.stderr

            # Cache pod-namespace mapping
            if 'kubectl get pods' in cmd and result.returncode == 0:
                lines = output.split('\n')
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 1:
                        pod_name = parts[0]
                        if '-n ' in cmd:
                            ns = cmd.split('-n ')[1].split()[0]
                            self._cache_pod_namespace(pod_name, ns)
                        elif 'NAMESPACE' in lines[0]:
                            ns_idx = lines[0].split().index('NAMESPACE')
                            if len(parts) > ns_idx:
                                self._cache_pod_namespace(pod_name, parts[ns_idx])

            # Retry with namespace if forbidden
            if 'forbidden' in output.lower() and namespace and 'kubectl' in cmd:
                if '-n' not in cmd and '--namespace' not in cmd:
                    cmd_parts = cmd.split()
                    for i, part in enumerate(cmd_parts):
                        if part in ['get', 'describe', 'logs']:
                            cmd_parts.insert(i+2, f'-n {namespace}')
                            break
                    cmd = ' '.join(cmd_parts)
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, env=env)
                    output = result.stdout if result.returncode == 0 else result.stderr

            # Auto-detect namespace for pod logs
            if 'kubectl logs' in cmd and '-n' not in cmd and '--namespace' not in cmd:
                pod_match = re.search(r'kubectl logs\s+(\S+)', cmd)
                if pod_match:
                    pod_name = pod_match.group(1)
                    detected_ns = self._get_pod_namespace(pod_name)
                    cmd = cmd.replace(f'kubectl logs {pod_name}', f'kubectl logs {pod_name} -n {detected_ns}')
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, env=env)
                    output = result.stdout if result.returncode == 0 else result.stderr
                    output = f"[Auto-detected namespace: {detected_ns}]\n\n" + output

            # Add NAMESPACE column for scoped users
            if namespace and namespace != 'default':
                if result.returncode == 0 and 'kubectl get pods' in cmd and '-n' in cmd and 'NAME' in output:
                    lines = output.split('\n')
                    if lines and 'NAMESPACE' not in lines[0]:
                        lines[0] = 'NAMESPACE   ' + lines[0]
                        for i in range(1, len(lines)):
                            if lines[i].strip():
                                lines[i] = f'{namespace:<12}' + lines[i]
                    output = '\n'.join(lines)

            self.last_command = cmd
            self.last_output = output
            self.conversation_memory.append({
                'command': cmd, 'output': output[:500],
                'timestamp': datetime.now().isoformat()
            })
            if len(self.conversation_memory) > 10:
                self.conversation_memory.pop(0)

            suggestions = self.analyze_output_and_suggest(cmd, output)
            return output + suggestions
        except Exception as e:
            return f"Error: {e}"

    def _cache_pod_namespace(self, pod_name: str, namespace: str):
        self.pod_namespace_cache[pod_name] = namespace
        if self.redis_client:
            try:
                self.redis_client.hset('pod_namespace_map', pod_name, namespace)
                self.redis_client.expire('pod_namespace_map', 3600)
            except:
                pass

    def _get_pod_namespace(self, pod_name: str) -> str:
        if pod_name in self.pod_namespace_cache:
            return self.pod_namespace_cache[pod_name]
        if self.redis_client:
            try:
                ns = self.redis_client.hget('pod_namespace_map', pod_name)
                if ns:
                    self.pod_namespace_cache[pod_name] = ns
                    return ns
            except:
                pass
        try:
            result = subprocess.run(
                f"kubectl get pods -A | grep {pod_name} | head -1",
                shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout:
                parts = result.stdout.split()
                if len(parts) >= 2:
                    namespace = parts[0]
                    self._cache_pod_namespace(pod_name, namespace)
                    return namespace
        except:
            pass
        return "default"

    def get_user_namespace(self, username: str) -> str:
        try:
            kubeconfig_path = auth_manager.get_user_kubeconfig(username)
            if kubeconfig_path:
                with open(kubeconfig_path, 'r') as f:
                    content = f.read()
                    match = re.search(r'namespace:\s*(\S+)', content)
                    if match:
                        return match.group(1)
            return None
        except:
            return None

    def _try_mcp_operation(self, query: str, query_lower: str) -> str:
        if not self.mcp_enabled:
            return None
        try:
            if 'list' in query_lower and 'pod' in query_lower:
                namespace = self._extract_namespace_from_query(query)
                result = self.k8s_mcp.get_pods(namespace)
                return f"**Pods in {namespace}:** (via MCP Server)\n\n{result}"
            if 'log' in query_lower and 'pod' in query_lower:
                pod_name = self._extract_pod_name_from_query(query)
                namespace = self._extract_namespace_from_query(query)
                if pod_name:
                    result = self.k8s_mcp.get_pod_logs(namespace, pod_name)
                    return f"**Logs for {pod_name} in {namespace}:** (via MCP Server)\n\n{result[:2000]}"
            if 'restart' in query_lower and 'deployment' in query_lower:
                deployment = self._extract_deployment_from_query(query)
                namespace = self._extract_namespace_from_query(query)
                if deployment:
                    result = self.k8s_mcp.restart_deployment(namespace, deployment)
                    return f"**Restart Result:** (via MCP Server)\n\n{result}"
            if 'scale' in query_lower:
                deployment = self._extract_deployment_from_query(query)
                replicas = self._extract_replicas_from_query(query)
                namespace = self._extract_namespace_from_query(query)
                if deployment and replicas:
                    result = self.k8s_mcp.scale_deployment(namespace, deployment, replicas)
                    return f"**Scale Result:** (via MCP Server)\n\n{result}"
            if 'node' in query_lower and 'list' in query_lower:
                result = self.k8s_mcp.get_nodes()
                return f"**Cluster Nodes:** (via MCP Server)\n\n{result}"
            if 'event' in query_lower:
                namespace = self._extract_namespace_from_query(query)
                result = self.k8s_mcp.get_events(namespace)
                return f"**Recent Events in {namespace}:** (via MCP Server)\n\n{result}"
        except Exception as e:
            print(f"MCP operation error: {e}")
        return None

    def _extract_namespace_from_query(self, query: str) -> str:
        match = re.search(r'namespace[:\s]+(\S+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r'\sin\s+(\S+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        return "default"

    def _extract_pod_name_from_query(self, query: str) -> str:
        match = re.search(r'(?:logs?\s+(?:of\s+|for\s+)?|pod\s+)([a-z0-9-]+)', query, re.IGNORECASE)
        if match:
            pod_name = match.group(1)
            if pod_name not in ['pod', 'pods', 'of', 'for', 'in', 'the']:
                return pod_name
        return None

    def _extract_deployment_from_query(self, query: str) -> str:
        match = re.search(r'deployment[:\s]+(\S+)', query, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_replicas_from_query(self, query: str) -> int:
        match = re.search(r'(\d+)\s*replica', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r'to\s+(\d+)', query, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def diagnose_issue(self, query: str) -> str:
        query_lower = query.lower()
        if 'node' in query_lower and ('not ready' in query_lower or 'down' in query_lower or 'notready' in query_lower):
            return """🔍 Node Issue Detected

**Problem:** Kubelet stopped posting node status

**Fix Steps:**
1. SSH to the node:
   ssh <node-name>
2. Check kubelet status:
   sudo systemctl status kubelet
3. Restart kubelet:
   sudo systemctl restart kubelet
4. Verify node is back:
   kubectl get nodes"""

        if 'imagepull' in query_lower or 'image pull' in query_lower:
            return """🔍 ImagePullBackOff Issue

**Problem:** Unauthorized access to container registry

**Fix:**
kubectl create secret docker-registry registry-secret \\
  --docker-server=<your-registry-url> \\
  --docker-username=<username> \\
  --docker-password=<password> \\
  -n <namespace>

kubectl patch serviceaccount default -n <namespace> \\
  -p '{"imagePullSecrets": [{"name": "registry-secret"}]}'

kubectl delete pods -n <namespace> --all"""

        if 'pending' in query_lower or 'not scheduling' in query_lower:
            return """🔍 Pod Pending Issue

**Possible Reasons:**
1. NotReady nodes reducing capacity
2. Control plane taint (not schedulable)
3. Pod anti-affinity rules

**Fix Options:**
1. Fix NotReady nodes first
2. Check anti-affinity: kubectl get pod <name> -n <ns> -o yaml | grep -A 10 affinity
3. Add more worker nodes"""

        if 'hpa' in query_lower or 'metrics' in query_lower or 'autoscal' in query_lower:
            return """🔍 HPA Metrics Issue

**Fix - Install Metrics Server:**
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

**Verify:**
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
kubectl top pods -A"""

        if 'loadbalancer' in query_lower:
            return """🔍 LoadBalancer Services Pending

**Fix - Install MetalLB:**
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml

**Configure IP Pool:**
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: metallb-system
spec:
  addresses:
  - 10.0.0.100-10.0.0.200
EOF"""
        return None

    def process_query(self, query: str, username: str = None) -> str:
        query_lower = query.lower()
        self.conversation_memory.append({
            'query': query, 'response': '',
            'timestamp': datetime.now().isoformat()
        })

        # Memory/history
        if 'last' in query_lower or 'previous' in query_lower or 'again' in query_lower:
            if self.last_command:
                response = f"**Last command:** {self.last_command}\n\n**Output:**\n{self.last_output}"
                self.conversation_memory[-1]['response'] = response
                return response
            return "No previous command in memory."

        if 'history' in query_lower or 'show memory' in query_lower:
            if not self.conversation_memory:
                return "No command history yet."
            history = "**Command History:**\n\n"
            for i, item in enumerate(reversed(self.conversation_memory[-5:]), 1):
                history += f"{i}. {item.get('command', item.get('query', 'N/A'))}\n   Time: {item['timestamp']}\n\n"
            return history

        if 'recommend' in query_lower or 'suggest' in query_lower or 'improve' in query_lower:
            return self.get_cluster_recommendations()

        # Direct kubectl
        if query.strip().startswith('kubectl '):
            response = self.execute_command(query.strip(), username)
            self.conversation_memory[-1]['response'] = response
            return response

        # Direct docker
        if query.strip().startswith('docker '):
            response = self.execute_command(query.strip(), username)
            self.conversation_memory[-1]['response'] = response
            return response

        # LLM analysis for natural language
        if self.llm_enabled:
            llm_analysis = self.analyze_with_llm(query)
            if llm_analysis.get('use_llm'):
                intent = llm_analysis.get('intent', '')
                if llm_analysis.get('needs_kubectl') and llm_analysis.get('suggested_command'):
                    cmd = llm_analysis['suggested_command']
                    explanation = llm_analysis.get('explanation', '')
                    response = f"**Understanding:** {explanation}\n\n**Executing:** `{cmd}`\n\n"
                    response += self.execute_command(cmd, username)
                    self.conversation_memory[-1]['response'] = response
                    return response
                if intent in ['log_analysis', 'troubleshooting']:
                    context = self.get_rag_context(query)
                    prompt = f"""You are an expert DevOps engineer. Query: {query}
Provide: 1. Root cause analysis 2. Step-by-step fix 3. Prevention tips"""
                    response = self.ask_llm(prompt, context)
                    self.conversation_memory[-1]['response'] = response
                    return response
                if intent == 'general_question':
                    context = self.get_rag_context(query)
                    response = self.ask_llm(f"Answer this DevOps question:\n{query}\nProvide practical, actionable advice.", context)
                    self.conversation_memory[-1]['response'] = response
                    return response

        # MCP operations
        if self.mcp_enabled and any(w in query_lower for w in ['pod', 'node', 'deployment', 'scale', 'restart', 'event']):
            mcp_response = self._try_mcp_operation(query, query_lower)
            if mcp_response:
                self.conversation_memory[-1]['response'] = mcp_response
                return mcp_response

        # Troubleshooting
        diagnosis = self.diagnose_issue(query)
        if diagnosis:
            self.conversation_memory[-1]['response'] = diagnosis
            return diagnosis

        # Cluster health
        if 'health' in query_lower or 'status' in query_lower or 'check cluster' in query_lower:
            output = self.execute_command("kubectl get nodes", username)
            output += "\n\n" + self.execute_command("kubectl get pods -A | grep -v Running | grep -v Completed | head -10", username)
            issues = []
            if 'NotReady' in output:
                issues.append("⚠️ Node NotReady detected")
            if 'ImagePullBackOff' in output or 'ErrImagePull' in output:
                issues.append("⚠️ ImagePullBackOff detected")
            if 'Pending' in output:
                issues.append("⚠️ Pod Pending detected")
            if 'CrashLoopBackOff' in output:
                issues.append("⚠️ CrashLoopBackOff detected")
            response = f"**Cluster Health:**\n{output}\n\n**Issues Found:**\n" + "\n".join(issues) if issues else f"**Cluster Health:**\n{output}\n\n✅ No critical issues found"
            self.conversation_memory[-1]['response'] = response
            return response

        # Resource queries
        if 'node' in query_lower:
            response = self.execute_command("kubectl describe nodes" if 'describe' in query_lower else "kubectl get nodes -o wide", username)
            self.conversation_memory[-1]['response'] = response
            return response

        if 'pod' in query_lower:
            if 'problem' in query_lower or 'issue' in query_lower or 'fail' in query_lower or 'error' in query_lower:
                return self.execute_command("kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded", username)
            if 'log' in query_lower:
                parts = query.lower().split()
                pod_name = namespace = None
                if 'pod' in parts:
                    idx = parts.index('pod')
                    if idx + 1 < len(parts):
                        pod_name = parts[idx + 1]
                if 'in' in parts:
                    idx = parts.index('in')
                    if idx + 1 < len(parts):
                        namespace = parts[idx + 1]
                if pod_name:
                    return self.execute_command(f"kubectl logs {pod_name} -n {namespace or 'default'} --tail=100", username)
                return "Specify: logs pod <pod-name> in <namespace>"
            if 'describe' in query_lower:
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() == 'pod' and i + 1 < len(words):
                        pod_name = words[i + 1]
                        namespace = 'default'
                        for j, w in enumerate(words):
                            if w.lower() in ['namespace', 'ns', 'in', '-n'] and j + 1 < len(words):
                                namespace = words[j + 1]
                        return self.execute_command(f"kubectl describe pod {pod_name} -n {namespace}", username)
                return "Specify: 'describe pod <pod-name>'"
            return self.execute_command("kubectl get pods -A", username)

        if 'ingress' in query_lower:
            return self.execute_command("kubectl get ingress -A", username)
        if 'service' in query_lower or 'svc' in query_lower:
            return self.execute_command("kubectl get svc -A", username)
        if 'deployment' in query_lower or 'deploy' in query_lower:
            return self.execute_command("kubectl get deployments -A", username)
        if 'event' in query_lower:
            return self.execute_command("kubectl get events -A --sort-by='.lastTimestamp' | tail -20", username)

        if 'help' in query_lower:
            return """**DevOps AI Agent - Available Commands:**

**Direct Commands:**
• kubectl get pods -A
• kubectl logs <pod-name> -n <namespace>
• kubectl describe pod <pod-name>
• docker ps

**Memory Commands:**
• history - Show last 5 commands
• last command - Show previous output

**Cluster Insights:**
• recommend - Get cluster improvement suggestions
• check cluster health

**Troubleshooting:**
• Fix node not ready
• Fix imagepullbackoff
• Fix pending pods

**Smart Features:**
✨ Remembers commands
✨ Auto-suggests fixes
✨ AI-powered analysis (LLM)
✨ MCP Server integration"""

        # LLM fallback
        if self.llm_enabled:
            context = self.get_rag_context(query)
            response = self.ask_llm(f"You are a Kubernetes cluster assistant. Answer: {query}\nProvide clear, actionable answers.", context)
            self.conversation_memory[-1]['response'] = response
            return response

        return "I can help with your cluster. Type 'help' for commands or run any kubectl/docker command directly."


agent = DevOpsAIAgent()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username', '')
        password = data.get('password', '')
        k8s_token = data.get('k8s_token', '')
        k8s_server = data.get('k8s_server', 'https://kubernetes.default.svc')

        if auth_manager.verify_user(username, password):
            namespace = None
            try:
                import base64
                token_parts = k8s_token.split('.')
                if len(token_parts) >= 2:
                    payload = token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)
                    decoded = base64.b64decode(payload)
                    token_data = json.loads(decoded)
                    if 'kubernetes.io' in token_data and 'namespace' in token_data['kubernetes.io']:
                        namespace = token_data['kubernetes.io']['namespace']
            except:
                pass

            kubeconfig = auth_manager.create_kubeconfig(username, k8s_token, k8s_server, namespace)
            auth_manager.save_user_kubeconfig(username, kubeconfig)
            session['username'] = username
            session['logged_in'] = True
            session['namespace'] = namespace
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def home():
    username = session.get('username')
    namespace = session.get('namespace')
    is_readonly = namespace not in [None, 'default']
    return render_template('index.html', username=username, is_readonly=is_readonly)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_message = request.json.get('message', '')
    username = session.get('username')
    response = agent.process_query(user_message, username)
    return jsonify({'response': response})

@app.route('/logs', methods=['POST'])
@login_required
def get_logs():
    pod = request.json.get('pod', '')
    namespace = request.json.get('namespace', '')
    lines = request.json.get('lines', 100)
    username = session.get('username')
    cmd = f'kubectl logs {pod} -n {namespace} --tail={lines}'
    logs = agent.execute_command(cmd, username)
    return jsonify({'logs': logs})

@app.route('/describe', methods=['POST'])
@login_required
def describe_pod():
    pod = request.json.get('pod', '')
    namespace = request.json.get('namespace', '')
    username = session.get('username')
    cmd = f'kubectl describe pod {pod} -n {namespace}'
    output = agent.execute_command(cmd, username)
    return jsonify({'output': output})

@app.route('/exec', methods=['POST'])
@login_required
def exec_pod():
    pod = request.json.get('pod', '')
    namespace = request.json.get('namespace', '')
    command = request.json.get('command', '')
    username = session.get('username')
    command = command.replace("'", "'\\''")
    cmd = f"kubectl exec {pod} -n {namespace} -- sh -c '{command}'"
    output = agent.execute_command(cmd, username)
    return jsonify({'output': output})

@app.route('/debug', methods=['GET'])
@login_required
def debug():
    username = session.get('username')
    namespace = session.get('namespace')
    kubeconfig = auth_manager.get_user_kubeconfig(username)
    detected_ns = agent.get_user_namespace(username)
    return jsonify({
        'username': username,
        'session_namespace': namespace,
        'detected_namespace': detected_ns,
        'kubeconfig_path': kubeconfig,
        'kubeconfig_exists': os.path.exists(kubeconfig) if kubeconfig else False
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
