# IntelliWeather Deployment Guide

This guide covers deploying IntelliWeather to various environments.

## Table of Contents

- [Quick Start (Docker)](#quick-start-docker)
- [Production Deployment (Kubernetes)](#production-deployment-kubernetes)
- [Cloud Providers](#cloud-providers)
- [Environment Configuration](#environment-configuration)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Docker)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Development

```bash
# Clone the repository
git clone https://github.com/CodersAcademy006/Weather-API.git
cd Weather-API

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
open http://localhost:8000
```

### Production (Single Node)

```bash
# Build production image
docker build -t intelliweather:latest .

# Run with production settings
docker run -d \
  --name intelliweather \
  -p 8000:8000 \
  -e DEBUG=false \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e LOG_LEVEL=INFO \
  -v intelliweather-data:/app/data \
  intelliweather:latest
```

### With NGINX Load Balancer

```bash
# Scale to 3 instances with NGINX
docker-compose -f docker-compose.yml up -d --scale app=3
```

---

## Production Deployment (Kubernetes)

### Prerequisites

- Kubernetes 1.25+
- kubectl configured
- Helm 3.x (optional)

### Using kubectl

```bash
# Create namespace
kubectl create namespace intelliweather

# Create secrets (IMPORTANT: use your own values!)
kubectl create secret generic intelliweather-secrets \
  --namespace intelliweather \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=redis-url="" \
  --from-literal=sentry-dsn=""

# Apply manifests
kubectl apply -f k8s/deployment.yaml --namespace intelliweather

# Check status
kubectl get pods -n intelliweather
kubectl get svc -n intelliweather
```

### Using Helm

```bash
# Add/update dependencies
cd helm/intelliweather
helm dependency update

# Install
helm install intelliweather . \
  --namespace intelliweather \
  --create-namespace \
  --values values.yaml \
  --set image.tag=v3.0.0

# Upgrade
helm upgrade intelliweather . \
  --namespace intelliweather \
  --set image.tag=v3.1.0

# Uninstall
helm uninstall intelliweather --namespace intelliweather
```

### Local Development (kind/minikube)

```bash
# Using the provided script
cd k8s/local
chmod +x local-setup.sh

# Full setup
./local-setup.sh setup

# Port forward to access
./local-setup.sh forward

# Cleanup
./local-setup.sh cleanup
```

---

## Cloud Providers

### AWS (EKS)

```bash
# Create EKS cluster
eksctl create cluster \
  --name intelliweather \
  --region us-east-1 \
  --nodes 3

# Configure kubectl
aws eks update-kubeconfig --name intelliweather --region us-east-1

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Google Cloud (GKE)

```bash
# Create GKE cluster
gcloud container clusters create intelliweather \
  --zone us-central1-a \
  --num-nodes 3

# Get credentials
gcloud container clusters get-credentials intelliweather --zone us-central1-a

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Azure (AKS)

```bash
# Create AKS cluster
az aks create \
  --resource-group intelliweather-rg \
  --name intelliweather \
  --node-count 3

# Get credentials
az aks get-credentials --resource-group intelliweather-rg --name intelliweather

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### DigitalOcean (DOKS)

```bash
# Create cluster via doctl
doctl kubernetes cluster create intelliweather \
  --region nyc1 \
  --node-pool "name=pool;size=s-2vcpu-4gb;count=3"

# Deploy
kubectl apply -f k8s/deployment.yaml
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secure random key for sessions | (required) |
| `APP_HOST` | Bind address | `0.0.0.0` |
| `APP_PORT` | Port number | `8000` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (json/text) | `json` |
| `DATA_DIR` | Data directory path | `/app/data` |
| `REDIS_URL` | Redis connection URL | (none) |
| `SENTRY_DSN` | Sentry error tracking | (none) |
| `CACHE_TTL_SECONDS` | Cache TTL | `3600` |
| `SESSION_TIMEOUT_SECONDS` | Session timeout | `86400` |
| `RATE_LIMIT_PER_MIN` | Rate limit per IP | `60` |

### Production Configuration

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intelliweather-config
data:
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  CACHE_TTL_SECONDS: "3600"
  SESSION_TIMEOUT_SECONDS: "86400"
  RATE_LIMIT_PER_MIN: "100"
```

---

## Health Checks & Monitoring

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `/healthz` | Liveness check |
| `/metrics` | Application metrics |
| `/metrics/prometheus` | Prometheus format |

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'intelliweather'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

---

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: intelliweather
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: intelliweather
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment intelliweather --replicas=5

# With Docker Compose
docker-compose up -d --scale app=5
```

---

## Troubleshooting

### Common Issues

#### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs -f deployment/intelliweather

# Check events
kubectl describe pod <pod-name>

# Common causes:
# - Missing SECRET_KEY
# - Invalid configuration
# - Resource limits too low
```

#### Connection Refused

```bash
# Check service
kubectl get svc intelliweather

# Check endpoints
kubectl get endpoints intelliweather

# Port forward for testing
kubectl port-forward svc/intelliweather 8080:80
```

#### High Latency

```bash
# Check resource usage
kubectl top pods

# Check cache hit ratio
curl http://localhost:8000/metrics | grep cache_

# Consider:
# - Increasing replicas
# - Enabling Redis cache
# - Increasing resource limits
```

### Useful Commands

```bash
# Get all resources
kubectl get all -n intelliweather

# Describe deployment
kubectl describe deployment intelliweather

# View logs
kubectl logs -f -l app=intelliweather

# Execute into pod
kubectl exec -it deployment/intelliweather -- /bin/bash

# Restart deployment
kubectl rollout restart deployment/intelliweather

# Check rollout status
kubectl rollout status deployment/intelliweather
```

---

## Security Recommendations

1. **TLS/SSL**: Always use HTTPS in production
2. **Secrets Management**: Use Kubernetes Secrets or external secret managers
3. **Network Policies**: Restrict pod-to-pod communication
4. **Pod Security**: Run as non-root, read-only filesystem
5. **Image Scanning**: Scan images for vulnerabilities

```yaml
# Example: Enable TLS with cert-manager
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - weather.example.com
      secretName: intelliweather-tls
```

---

## Support

- **Documentation**: [README.md](../README.md)
- **Issues**: [GitHub Issues](https://github.com/CodersAcademy006/Weather-API/issues)
- **API Docs**: `/docs` endpoint
