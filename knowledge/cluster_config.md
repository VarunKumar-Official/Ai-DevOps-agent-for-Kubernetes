# Sample Kubernetes Cluster Configuration
# Customize this file for your environment

## Cluster Nodes
- **master-node-01** - Control Plane (Ready)
  - IP: 10.0.0.10
  - Role: control-plane

- **worker-node-01** - Worker (Ready)
  - IP: 10.0.0.11

- **worker-node-02** - Worker (Ready)
  - IP: 10.0.0.12

- **worker-node-03** - Worker (Ready)
  - IP: 10.0.0.13

## Namespaces
- default
- kube-system
- monitoring
- ingress-nginx
- app-namespace

## Common Issues & Fixes

### 1. Node NotReady
```bash
ssh <node-name>
sudo systemctl status kubelet
sudo systemctl restart kubelet
```

### 2. ImagePullBackOff
```bash
kubectl create secret docker-registry registry-secret \
  --docker-server=<your-registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n <namespace>
```

### 3. Pod Pending
- Check node resources: `kubectl describe nodes`
- Check pod events: `kubectl describe pod <name> -n <namespace>`

### 4. Install Metrics Server
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
