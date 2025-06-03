#!/bin/bash

# Enterprise RAG System - Deployment Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check environment argument
if [ "$#" -ne 1 ]; then
    echo -e "${RED}Usage: $0 [staging|production]${NC}"
    exit 1
fi

ENVIRONMENT=$1

# Validate environment
if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
    echo "Environment must be 'staging' or 'production'"
    exit 1
fi

echo -e "${BLUE}🚀 Deploying Enterprise RAG System to $ENVIRONMENT${NC}"

# Load environment-specific configuration
if [ "$ENVIRONMENT" == "production" ]; then
    ENV_FILE=".env.prod"
    COMPOSE_FILE="docker/docker-compose.prod.yml"
    REGISTRY="your-registry.com"
    TAG="latest"
else
    ENV_FILE=".env.staging"
    COMPOSE_FILE="docker/docker-compose.staging.yml"
    REGISTRY="your-registry.com"
    TAG="staging"
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Environment file $ENV_FILE not found${NC}"
    exit 1
fi

# Run tests first
echo -e "${YELLOW}Running tests...${NC}"
make test
if [ $? -ne 0 ]; then
    echo -e "${RED}Tests failed! Aborting deployment${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Tests passed${NC}"

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t enterprise-rag-system:$TAG -f docker/Dockerfile .
echo -e "${GREEN}✓ Docker image built${NC}"

# Tag and push to registry
echo -e "${YELLOW}Pushing to registry...${NC}"
docker tag enterprise-rag-system:$TAG $REGISTRY/enterprise-rag-system:$TAG
docker push $REGISTRY/enterprise-rag-system:$TAG
echo -e "${GREEN}✓ Image pushed to registry${NC}"

# Deploy based on environment
if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "${YELLOW}Deploying to production cluster...${NC}"
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/service.yaml
    kubectl apply -f k8s/ingress.yaml
    
    # Wait for rollout
    kubectl rollout status deployment/enterprise-rag-system -n rag-system
    
    echo -e "${GREEN}✓ Production deployment complete${NC}"
    
elif [ "$ENVIRONMENT" == "staging" ]; then
    echo -e "${YELLOW}Deploying to staging server...${NC}"
    
    # Copy files to staging server
    rsync -avz --exclude='data/' --exclude='logs/' --exclude='.env' \
        ./ staging-server:/opt/enterprise-rag-system/
    
    # Deploy on staging server
    ssh staging-server << EOF
        cd /opt/enterprise-rag-system
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE pull
        docker-compose -f $COMPOSE_FILE up -d
        docker-compose -f $COMPOSE_FILE ps
EOF
    
    echo -e "${GREEN}✓ Staging deployment complete${NC}"
fi

# Run post-deployment checks
echo -e "${YELLOW}Running post-deployment checks...${NC}"

# Wait for service to be ready
sleep 30

# Health check
if [ "$ENVIRONMENT" == "production" ]; then
    HEALTH_URL="https://api.yourcompany.com/health"
else
    HEALTH_URL="https://staging-api.yourcompany.com/health"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

# Run smoke tests
echo -e "${YELLOW}Running smoke tests...${NC}"
python scripts/smoke_tests.py --environment $ENVIRONMENT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Smoke tests passed${NC}"
else
    echo -e "${RED}❌ Smoke tests failed${NC}"
    exit 1
fi

# Final message
echo -e "\n${GREEN}🎉 Deployment to $ENVIRONMENT completed successfully!${NC}"
echo -e "\nDeployment summary:"
echo -e "- Environment: $ENVIRONMENT"
echo -e "- Image: $REGISTRY/enterprise-rag-system:$TAG"
echo -e "- Health check: ✓"
echo -e "- Smoke tests: ✓"

# Send notification (optional)
if command -v slack-cli &> /dev/null; then
    slack-cli send "Enterprise RAG System deployed to $ENVIRONMENT successfully! 🚀"
fi