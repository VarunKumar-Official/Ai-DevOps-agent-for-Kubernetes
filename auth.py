"""
Authentication module for DevOps AI Agent
Supports user login with Kubernetes RBAC credentials
"""

import os
import hashlib
import secrets
from functools import wraps
from flask import session, redirect, url_for, request

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.txt')
KUBECONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kubeconfigs')

class AuthManager:
    def __init__(self):
        self.sessions = {}
        self.secret_key = secrets.token_hex(32)

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_user(self, username, password):
        if not os.path.exists(USERS_FILE):
            return False
        with open(USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(':')
                if len(parts) >= 2 and parts[0] == username:
                    return self.hash_password(password) == parts[1]
        return False

    def create_kubeconfig(self, username, token, server, namespace=None):
        namespace_line = f"\n    namespace: {namespace}" if namespace else ""
        return f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    server: {server}
    insecure-skip-tls-verify: true
  name: k8s-cluster
contexts:
- context:
    cluster: k8s-cluster
    user: {username}{namespace_line}
  name: {username}@k8s-cluster
current-context: {username}@k8s-cluster
users:
- name: {username}
  user:
    token: {token}
"""

    def save_user_kubeconfig(self, username, kubeconfig_content):
        os.makedirs(KUBECONFIG_DIR, exist_ok=True)
        kubeconfig_path = os.path.join(KUBECONFIG_DIR, f'{username}.kubeconfig')
        with open(kubeconfig_path, 'w') as f:
            f.write(kubeconfig_content)
        os.chmod(kubeconfig_path, 0o600)
        return kubeconfig_path

    def get_user_kubeconfig(self, username):
        kubeconfig_path = os.path.join(KUBECONFIG_DIR, f'{username}.kubeconfig')
        return kubeconfig_path if os.path.exists(kubeconfig_path) else None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
