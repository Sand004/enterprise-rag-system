#!/usr/bin/env python3
"""Download required models for the RAG system"""

import os
import sys
from pathlib import Path

import requests
from huggingface_hub import snapshot_download
from loguru import logger
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings


class ModelDownloader:
    """Handle model downloads"""
    
    def __init__(self):
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
    def download_embedding_models(self):
        """Download embedding models"""
        logger.info("Downloading embedding models...")
        
        models = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "BAAI/bge-large-en-v1.5",
        ]
        
        for model_name in models:
            logger.info(f"Downloading {model_name}...")
            model_path = self.models_dir / model_name.replace("/", "_")
            
            if model_path.exists():
                logger.info(f"Model {model_name} already exists, skipping")
                continue
                
            # Download using sentence-transformers
            model = SentenceTransformer(model_name)
            model.save(str(model_path))
            logger.success(f"Downloaded {model_name}")
            
    def download_llm_models(self):
        """Download LLM models (if not using vLLM)"""
        logger.info("Downloading LLM models...")
        
        # For vLLM, models are typically downloaded on first use
        # This is a placeholder for alternative model downloads
        
        if settings.llm_provider == "ollama":
            logger.info("Using Ollama - models will be pulled on first use")
        elif settings.llm_provider == "huggingface":
            # Example: Download smaller models for testing
            models = [
                "microsoft/phi-2",
                "mistralai/Mistral-7B-Instruct-v0.1"
            ]
            
            for model_name in models:
                logger.info(f"Downloading {model_name}...")
                model_path = self.models_dir / model_name.replace("/", "_")
                
                if model_path.exists():
                    logger.info(f"Model {model_name} already exists, skipping")
                    continue
                    
                try:
                    snapshot_download(
                        repo_id=model_name,
                        local_dir=str(model_path),
                        local_dir_use_symlinks=False
                    )
                    logger.success(f"Downloaded {model_name}")
                except Exception as e:
                    logger.error(f"Failed to download {model_name}: {e}")
                    
    def download_reranking_models(self):
        """Download reranking models"""
        logger.info("Downloading reranking models...")
        
        models = [
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "BAAI/bge-reranker-large"
        ]
        
        for model_name in models:
            logger.info(f"Downloading {model_name}...")
            model_path = self.models_dir / model_name.replace("/", "_")
            
            if model_path.exists():
                logger.info(f"Model {model_name} already exists, skipping")
                continue
                
            try:
                snapshot_download(
                    repo_id=model_name,
                    local_dir=str(model_path),
                    local_dir_use_symlinks=False
                )
                logger.success(f"Downloaded {model_name}")
            except Exception as e:
                logger.error(f"Failed to download {model_name}: {e}")
                
    def verify_downloads(self):
        """Verify all required models are downloaded"""
        logger.info("Verifying model downloads...")
        
        required_models = [
            "sentence-transformers_all-MiniLM-L6-v2",
            "BAAI_bge-large-en-v1.5",
            "cross-encoder_ms-marco-MiniLM-L-6-v2"
        ]
        
        missing_models = []
        for model in required_models:
            model_path = self.models_dir / model
            if not model_path.exists():
                missing_models.append(model)
                
        if missing_models:
            logger.warning(f"Missing models: {missing_models}")
            return False
        else:
            logger.success("All required models are downloaded")
            return True


def main():
    """Main download function"""
    downloader = ModelDownloader()
    
    logger.info("Starting model downloads...")
    
    # Download different model types
    downloader.download_embedding_models()
    downloader.download_reranking_models()
    
    # Optionally download LLM models
    if "--include-llms" in sys.argv:
        downloader.download_llm_models()
        
    # Verify downloads
    if downloader.verify_downloads():
        logger.success("Model download completed successfully!")
        return 0
    else:
        logger.error("Some models failed to download")
        return 1


if __name__ == "__main__":
    sys.exit(main())