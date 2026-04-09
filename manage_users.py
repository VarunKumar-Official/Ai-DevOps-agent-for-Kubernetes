#!/usr/bin/env python3
"""
User management script for DevOps AI Agent
Add/remove users with hashed passwords
"""

import hashlib
import sys
import os

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.txt')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                if line.startswith(username + ':'):
                    print(f"❌ User '{username}' already exists!")
                    return False
    with open(USERS_FILE, 'a') as f:
        f.write(f"{username}:{hash_password(password)}\n")
    print(f"✅ User '{username}' added successfully!")
    return True

def list_users():
    if not os.path.exists(USERS_FILE):
        print("No users found.")
        return
    print("\n📋 Registered Users:")
    print("-" * 40)
    with open(USERS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                print(f"  • {line.split(':')[0]}")
    print("-" * 40)

def remove_user(username):
    if not os.path.exists(USERS_FILE):
        print("❌ No users file found!")
        return False
    lines = []
    found = False
    with open(USERS_FILE, 'r') as f:
        for line in f:
            if not line.startswith(username + ':'):
                lines.append(line)
            else:
                found = True
    if found:
        with open(USERS_FILE, 'w') as f:
            f.writelines(lines)
        print(f"✅ User '{username}' removed successfully!")
        return True
    print(f"❌ User '{username}' not found!")
    return False

def main():
    if len(sys.argv) < 2:
        print("DevOps AI Agent - User Management")
        print("\nUsage:")
        print("  python3 manage_users.py add <username> <password>")
        print("  python3 manage_users.py remove <username>")
        print("  python3 manage_users.py list")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == 'add':
        if len(sys.argv) != 4:
            print("❌ Usage: python3 manage_users.py add <username> <password>")
            sys.exit(1)
        add_user(sys.argv[2], sys.argv[3])
    elif command == 'remove':
        if len(sys.argv) != 3:
            print("❌ Usage: python3 manage_users.py remove <username>")
            sys.exit(1)
        remove_user(sys.argv[2])
    elif command == 'list':
        list_users()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
