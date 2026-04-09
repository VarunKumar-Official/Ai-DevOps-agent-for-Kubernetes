import time
import subprocess
import json
from agent import DevOpsAgent
from auto_remediation import AutoRemediation

class MonitoringAgent:
    def __init__(self, check_interval: int = 60, auto_remediate: bool = False):
        self.check_interval = check_interval
        self.agent = DevOpsAgent()
        self.remediator = AutoRemediation(auto_approve=auto_remediate)
        self.thresholds = {'restart_count': 5, 'error_rate': 10}

    def check_pod_health(self):
        try:
            result = subprocess.run(
                ['kubectl', 'get', 'pods', '-A', '-o', 'json'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                pods = json.loads(result.stdout)
                for pod in pods.get('items', []):
                    pod_name = pod['metadata']['name']
                    namespace = pod['metadata']['namespace']
                    status = pod.get('status', {})
                    phase = status.get('phase')
                    for container in status.get('containerStatuses', []):
                        restart_count = container.get('restartCount', 0)
                        state = container.get('state', {})
                        if restart_count >= self.thresholds['restart_count']:
                            print(f"\n⚠️  Alert: {pod_name} in {namespace} has {restart_count} restarts")
                            self.remediator.remediate('CrashLoopBackOff', pod_name, namespace)
                        if 'waiting' in state:
                            reason = state['waiting'].get('reason', '')
                            if reason in ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull']:
                                print(f"\n⚠️  Alert: {pod_name} in {namespace} - {reason}")
                                self.remediator.remediate(reason, pod_name, namespace)
                        if 'terminated' in state:
                            reason = state['terminated'].get('reason', '')
                            if reason == 'OOMKilled':
                                print(f"\n⚠️  Alert: {pod_name} in {namespace} - OOMKilled")
                                self.remediator.remediate('OOMKilled', pod_name, namespace)
                    if phase == 'Pending':
                        print(f"\n⚠️  Alert: {pod_name} in {namespace} is Pending")
                        self.remediator.remediate('Pending', pod_name, namespace)
        except Exception as e:
            print(f"Error checking pod health: {e}")

    def run(self):
        print(f"Starting monitoring agent (checking every {self.check_interval}s)")
        print("Press Ctrl+C to stop\n")
        try:
            while True:
                self.check_pod_health()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")

if __name__ == "__main__":
    import sys
    auto_remediate = '--auto' in sys.argv
    interval = 60
    if '--interval' in sys.argv:
        idx = sys.argv.index('--interval')
        interval = int(sys.argv[idx + 1])
    print(f"Auto-remediation: {'Enabled' if auto_remediate else 'Disabled'}")
    MonitoringAgent(check_interval=interval, auto_remediate=auto_remediate).run()
