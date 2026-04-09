import subprocess
import json
from typing import Dict, Optional

class AutoRemediation:
    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self.remediation_rules = {
            'CrashLoopBackOff': self.fix_crashloop,
            'ImagePullBackOff': self.fix_image_pull,
            'OOMKilled': self.fix_oom,
            'Pending': self.fix_pending_pod,
        }

    def fix_crashloop(self, pod_name: str, namespace: str) -> Dict:
        actions = [
            f"kubectl logs {pod_name} -n {namespace} --previous",
            f"kubectl describe pod {pod_name} -n {namespace}"
        ]
        results = []
        for cmd in actions:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            results.append(result.stdout)
        logs = results[0]
        if "connection refused" in logs.lower():
            return {"action": "restart_dependencies", "details": "Dependency service down"}
        elif "permission denied" in logs.lower():
            return {"action": "check_rbac", "details": "RBAC issue detected"}
        return {"action": "restart_pod", "command": f"kubectl delete pod {pod_name} -n {namespace}"}

    def fix_image_pull(self, pod_name: str, namespace: str) -> Dict:
        return {"action": "check_image", "suggestions": [
            "Verify image name and tag",
            "Check image registry credentials",
            "Ensure image exists in registry"
        ]}

    def fix_oom(self, pod_name: str, namespace: str) -> Dict:
        cmd = f"kubectl get pod {pod_name} -n {namespace} -o json"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        if result.returncode == 0:
            pod_data = json.loads(result.stdout)
            memory_limit = pod_data['spec']['containers'][0].get('resources', {}).get('limits', {}).get('memory', 'Not set')
            return {"action": "increase_memory", "current_limit": memory_limit, "suggestion": "Increase memory limit by 50%"}
        return {"action": "manual_review", "details": "Could not fetch pod details"}

    def fix_pending_pod(self, pod_name: str, namespace: str) -> Dict:
        cmd = f"kubectl describe pod {pod_name} -n {namespace}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        output = result.stdout
        if "Insufficient cpu" in output or "Insufficient memory" in output:
            return {"action": "scale_nodes", "details": "Insufficient cluster resources"}
        elif "no nodes available" in output:
            return {"action": "check_node_selectors", "details": "Node selector mismatch"}
        return {"action": "manual_review", "details": "Unknown pending reason"}

    def remediate(self, issue_type: str, pod_name: str, namespace: str) -> Optional[Dict]:
        if issue_type not in self.remediation_rules:
            return None
        print(f"\n🔧 Auto-remediation for {issue_type}: {pod_name}")
        result = self.remediation_rules[issue_type](pod_name, namespace)
        print(f"Action: {result.get('action')}")
        print(f"Details: {result.get('details', result.get('suggestion', 'N/A'))}")
        if 'command' in result:
            if self.auto_approve:
                print(f"Executing: {result['command']}")
                subprocess.run(result['command'].split())
            else:
                approval = input(f"\nExecute: {result['command']}? (yes/no): ")
                if approval.lower() == 'yes':
                    subprocess.run(result['command'].split())
        return result
