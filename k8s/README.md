# Kubernetes Deployment Files

This directory contains Kubernetes manifests for deploying the Enterprise RAG System.

## Structure

```
k8s/
├── namespace.yaml          # Namespace definition
├── configmap.yaml         # Configuration settings
├── secrets.yaml           # Secret template
├── deployments/
│   ├── api.yaml          # API server deployment
│   ├── vllm.yaml         # vLLM deployment
│   └── workers.yaml      # Background workers
├── services/
│   ├── api-service.yaml  # API service
│   └── internal.yaml     # Internal services
├── ingress/
│   └── ingress.yaml      # Ingress configuration
├── storage/
│   ├── postgres.yaml     # PostgreSQL StatefulSet
│   ├── qdrant.yaml       # Qdrant StatefulSet
│   ├── redis.yaml        # Redis deployment
│   └── minio.yaml        # MinIO deployment
└── monitoring/
    ├── prometheus.yaml   # Prometheus configuration
    └── grafana.yaml      # Grafana dashboards
```

## Deployment Order

1. Create namespace: `kubectl apply -f namespace.yaml`
2. Create secrets: `kubectl apply -f secrets.yaml`
3. Deploy storage: `kubectl apply -f storage/`
4. Deploy application: `kubectl apply -f deployments/`
5. Create services: `kubectl apply -f services/`
6. Setup ingress: `kubectl apply -f ingress/`
7. Deploy monitoring: `kubectl apply -f monitoring/`

## Configuration

Before deploying, ensure you have:
- Created necessary secrets
- Updated image references
- Configured resource limits
- Set up persistent volumes