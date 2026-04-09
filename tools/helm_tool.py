import subprocess
from typing import Dict, List

SAFE_COMMANDS = ['list', 'status', 'get', 'history', 'search']
RESTRICTED_COMMANDS = ['install', 'upgrade', 'rollback', 'uninstall', 'delete']

def execute_helm(args: List[str]) -> Dict:
    """Execute helm commands with safety checks"""
    if not args:
        return {"error": "No helm command provided"}

    command = args[0]

    if command in SAFE_COMMANDS:
        return _run_helm(args)
    elif command in RESTRICTED_COMMANDS:
        return {"needs_approval": True, "command": f"helm {' '.join(args)}"}
    else:
        return {"error": f"Unknown or restricted helm command: {command}"}

def _run_helm(args: List[str]) -> Dict:
    """Run helm command"""
    try:
        result = subprocess.run(
            ['helm'] + args,
            capture_output=True, text=True, timeout=30
        )
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"error": "Helm command timed out"}
    except FileNotFoundError:
        return {"error": "helm not found. Install from https://helm.sh"}
    except Exception as e:
        return {"error": str(e)}
