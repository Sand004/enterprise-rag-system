# Enterprise RAG System Deployment Guide

## Prerequisites

### Hardware Requirements

#### Minimum (Development)
- CPU: 8 cores
- RAM: 32GB
- Storage: 500GB SSD
- GPU: NVIDIA RTX 3090 (24GB VRAM)

#### Recommended (Production)
- CPU: 32 cores
- RAM: 128GB
- Storage: 2TB NVMe SSD
- GPU: 2x NVIDIA A100 (80GB) or 4x RTX 4090

### Software Requirements
- Docker 24.0+
- Docker Compose 2.20+
- Kubernetes 1.28+ (for K8s deployment)
- Python 3.10+
- NVIDIA Driver 530+
- CUDA 12.1+

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/enterprise-rag-system.git
cd enterprise-rag-system
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
vim .env
```

Key configurations to update:
- API keys (OpenAI, Cohere, etc.)
- Atlassian credentials
- Database passwords
- Encryption keys

### 3. Initialize System

```bash
# Run initialization script
./scripts/init_system.sh

# Download models (optional)
./scripts/init_system.sh --download-models
```

### 4. Start Services

```bash
# Start development environment
make dev-up

# Check service health
make logs
```

### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8080/health

# Access services
# API: http://localhost:8080
# API Docs: http://localhost:8080/docs
# MinIO: http://localhost:9001
# Redis Commander: http://localhost:8081
# pgAdmin: http://localhost:8082
```

## Docker Deployment

### Single Host Deployment

```bash
# Build images
make build

# Start production stack
docker-compose -f docker-compose.yml up -d

# Scale API servers
docker-compose up -d --scale app=3
```

### Docker Swarm Deployment

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker/docker-compose.prod.yml rag-system

# Check services
docker service ls
```

## Kubernetes Deployment

### 1. Prepare Cluster

```bash
# Create namespace
kubectl create namespace rag-system

# Create secrets
kubectl create secret generic rag-secrets \
  --from-env-file=.env \
  -n rag-system
```

### 2. Deploy Infrastructure

```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgres/

# Deploy Redis
kubectl apply -f k8s/redis/

# Deploy Qdrant
kubectl apply -f k8s/qdrant/

# Deploy MinIO
kubectl apply -f k8s/minio/
```

### 3. Deploy Application

```bash
# Deploy application
kubectl apply -f k8s/app/

# Deploy vLLM (GPU nodes)
kubectl apply -f k8s/vllm/

# Deploy ingress
kubectl apply -f k8s/ingress/
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n rag-system

# Check services
kubectl get svc -n rag-system

# Get ingress URL
kubectl get ingress -n rag-system
```

## Cloud Deployment

### AWS Deployment

#### Using EKS

```bash
# Create EKS cluster
eksctl create cluster \
  --name rag-cluster \
  --region us-east-1 \
  --node-group-name gpu-nodes \
  --node-type p3.8xlarge \
  --nodes 2

# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Deploy application
kubectl apply -f k8s/
```

#### Using EC2

```bash
# Launch GPU instance
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type p3.8xlarge \
  --key-name your-key \
  --security-groups rag-security-group

# Install dependencies
ssh ubuntu@instance-ip
sudo apt update
sudo apt install docker.io docker-compose

# Deploy application
git clone https://github.com/your-org/enterprise-rag-system.git
cd enterprise-rag-system
docker-compose up -d
```

### GCP Deployment

```bash
# Create GKE cluster
gcloud container clusters create rag-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-8 \
  --accelerator type=nvidia-tesla-v100,count=2

# Install NVIDIA drivers
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml

# Deploy application
kubectl apply -f k8s/
```

### Azure Deployment

```bash
# Create AKS cluster
az aks create \
  --resource-group rag-resources \
  --name rag-cluster \
  --node-count 3 \
  --node-vm-size Standard_NC6s_v3 \
  --enable-addons monitoring

# Deploy application
kubectl apply -f k8s/
```

## Production Configuration

### SSL/TLS Setup

```yaml
# k8s/ingress-tls.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: rag-tls-secret
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rag-api
            port:
              number: 8080
```

### Monitoring Setup

```bash
# Deploy Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace

# Deploy Grafana dashboards
kubectl apply -f monitoring/dashboards/

# Deploy alerts
kubectl apply -f monitoring/alerts/
```

### Backup Configuration

```bash
# PostgreSQL backup
kubectl apply -f k8s/backup/postgres-backup.yaml

# Qdrant backup
kubectl apply -f k8s/backup/qdrant-backup.yaml

# S3 sync for documents
aws s3 sync s3://rag-documents s3://rag-documents-backup \
  --storage-class GLACIER
```

## Performance Tuning

### vLLM Optimization

```yaml
# Optimal vLLM settings
env:
  - name: VLLM_ATTENTION_BACKEND
    value: "flashinfer"
  - name: TENSOR_PARALLEL_SIZE
    value: "4"
  - name: MAX_MODEL_LEN
    value: "32768"
  - name: GPU_MEMORY_UTILIZATION
    value: "0.95"
  - name: ENABLE_PREFIX_CACHING
    value: "true"
```

### Database Optimization

```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET max_connections = '200';
SELECT pg_reload_conf();
```

### Qdrant Optimization

```json
{
  "optimizers_config": {
    "indexing_threshold": 50000,
    "memmap_threshold": 100000,
    "max_optimization_threads": 8
  },
  "hnsw_config": {
    "m": 32,
    "ef_construct": 400,
    "ef": 256
  }
}
```

## Troubleshooting

### Common Issues

#### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA
nvcc --version

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

#### Memory Issues

```bash
# Check memory usage
free -h

# Check container limits
docker stats

# Adjust compose limits
vim docker-compose.yml
# Modify memory limits under deploy.resources
```

#### Slow Performance

```bash
# Check CPU usage
top

# Check disk I/O
iotop

# Check network
iftop

# Profile application
python -m cProfile -o profile.stats src/main.py
```

## Maintenance

### Regular Tasks

```bash
# Daily: Check logs
make logs | grep ERROR

# Weekly: Update dependencies
pip install --upgrade -r requirements.txt

# Monthly: Optimize databases
docker exec rag-postgres psql -U postgres -c "VACUUM ANALYZE;"

# Quarterly: Update models
python scripts/download_models.py
```

### Scaling Operations

```bash
# Scale API servers
kubectl scale deployment rag-api --replicas=5

# Scale vector database
kubectl scale statefulset qdrant --replicas=5

# Add GPU nodes
eksctl scale nodegroup \
  --cluster=rag-cluster \
  --name=gpu-nodes \
  --nodes=4
```