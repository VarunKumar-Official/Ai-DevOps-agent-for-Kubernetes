import subprocess
from typing import List, Dict

SAFE_COMMANDS = ['get', 'describe', 'logs', 'top']
RESTRICTED_COMMANDS = ['delete', 'scale', 'patch', 'apply', 'create', 'rollout']

def execute_kubectl(args: List[str]) -> Dict[str, str]:
    """Execute kubectl commands with safety restrictions"""
    if not args:
        return {"error": "No command provided"}

    command = args[0]

    if command in RESTRICTED_COMMANDS:
        return {"error": f"Command '{command}' requires approval", "requires_approval": True}

    if command not in SAFE_COMMANDS:
        return {"error": f"Command '{command}' not allowed"}

    try:
        result = subprocess.run(
            ['kubectl'] + args,
            capture_output=True, text=True, timeout=30
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

def execute_with_approval(args: List[str]) -> Dict[str, str]:
    """Execute restricted kubectl commands after approval"""
    try:
        result = subprocess.run(
            ['kubectl'] + args,
            capture_output=True, text=True, timeout=30
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except Exception as e:
        return {"error": str(e)}
