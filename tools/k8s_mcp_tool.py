#!/usr/bin/env python3
"""
K8s MCP Tool Integration for DevOps AI Agent
Connects to a K8s MCP Server running in your cluster
"""

import subprocess
import json
from typing import Dict, List, Optional

class K8sMCPTool:
    """Tool to interact with K8s MCP Server in your cluster"""

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.pod_name = self._get_mcp_pod()

    def _get_mcp_pod(self) -> str:
        """Get the current MCP server pod name"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pod", "-l", "app=k8s-mcp-server",
                 "-n", self.namespace, "-o", "jsonpath={.items[0].metadata.name}"],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"Error getting MCP pod: {e}")
            return ""

    def _call_mcp_tool(self, tool_name: str, **kwargs) -> str:
        """Call an MCP tool function"""
        args_str = ", ".join([f"{k}='{v}'" for k, v in kwargs.items()])
        python_cmd = f"""
import sys
sys.path.insert(0, '/app')
from server import init_k8s, {tool_name}
init_k8s()
print({tool_name}({args_str}))
"""
        try:
            result = subprocess.run(
                ["kubectl", "exec", "-n", self.namespace, self.pod_name,
                 "--", "python", "-c", python_cmd],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error calling MCP tool: {e}"

    def get_pods(self, namespace: str = "default") -> str:
        return self._call_mcp_tool("get_pods", namespace=namespace)

    def get_pod_logs(self, namespace: str, pod: str) -> str:
        return self._call_mcp_tool("get_pod_logs", namespace=namespace, pod=pod)

    def restart_deployment(self, namespace: str, deployment: str) -> str:
        return self._call_mcp_tool("restart_deployment", namespace=namespace, deployment=deployment)

    def scale_deployment(self, namespace: str, deployment: str, replicas: int) -> str:
        return self._call_mcp_tool("scale_deployment", namespace=namespace, deployment=deployment, replicas=replicas)

    def get_nodes(self) -> str:
        return self._call_mcp_tool("get_nodes")

    def get_events(self, namespace: str = "default") -> str:
        return self._call_mcp_tool("get_events", namespace=namespace)
