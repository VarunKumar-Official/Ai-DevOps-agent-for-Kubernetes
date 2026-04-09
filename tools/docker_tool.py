import subprocess
from typing import List, Dict

SAFE_COMMANDS = ['ps', 'logs', 'inspect', 'images', 'stats']
RESTRICTED_COMMANDS = ['rm', 'rmi', 'stop', 'kill', 'restart']

def execute_docker(args: List[str]) -> Dict[str, str]:
    """Execute docker commands with safety restrictions"""
    if not args:
        return {"error": "No command provided"}

    command = args[0]

    if command in RESTRICTED_COMMANDS:
        return {"error": f"Command '{command}' requires approval", "requires_approval": True}

    if command not in SAFE_COMMANDS:
        return {"error": f"Command '{command}' not allowed"}

    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True, text=True, timeout=30
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

def execute_with_approval(args: List[str]) -> Dict[str, str]:
    """Execute restricted docker commands after approval"""
    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True, text=True, timeout=30
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    except Exception as e:
        return {"error": str(e)}
