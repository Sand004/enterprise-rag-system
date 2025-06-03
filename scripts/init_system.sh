#!/bin/bash

# Enterprise RAG System - Initialization Script

set -e

echo "🚀 Initializing Enterprise RAG System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please update .env with your configuration${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p data/uploads data/processed data/cache
mkdir -p logs
mkdir -p models
mkdir -p config
echo -e "${GREEN}✓ Directories created${NC}"

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check Docker Compose installation
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check GPU availability (for vLLM)
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv
else
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected - vLLM will not work${NC}"
fi

# Pull Docker images
echo -e "${YELLOW}Pulling Docker images...${NC}"
docker-compose pull
echo -e "${GREEN}✓ Docker images pulled${NC}"

# Initialize databases
echo -e "${YELLOW}Starting database services...${NC}"
docker-compose up -d postgres redis qdrant minio

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose run --rm app alembic upgrade head
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Create MinIO bucket
echo -e "${YELLOW}Creating MinIO bucket...${NC}"
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/rag-documents --ignore-existing
echo -e "${GREEN}✓ MinIO bucket created${NC}"

# Initialize Qdrant collection
echo -e "${YELLOW}Initializing Qdrant collection...${NC}"
curl -X PUT 'http://localhost:6333/collections/enterprise_docs' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 3072,
      "distance": "Cosine"
    }
  }' || echo -e "${YELLOW}Collection may already exist${NC}"

echo -e "${GREEN}✓ Qdrant collection initialized${NC}"

# Download models (if specified)
if [ "$1" == "--download-models" ]; then
    echo -e "${YELLOW}Downloading models...${NC}"
    python scripts/download_models.py
    echo -e "${GREEN}✓ Models downloaded${NC}"
fi

# Final message
echo -e "\n${GREEN}🎉 Enterprise RAG System initialized successfully!${NC}"
echo -e "\nNext steps:"
echo -e "1. Update your .env file with API keys and configuration"
echo -e "2. Run 'make dev-up' to start the development environment"
echo -e "3. Access the API at http://localhost:8080"
echo -e "4. View API docs at http://localhost:8080/docs"

echo -e "\n${YELLOW}Optional tools:${NC}"
echo -e "- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo -e "- Redis Commander: http://localhost:8081"
echo -e "- pgAdmin: http://localhost:8082 (admin@example.com/admin)"