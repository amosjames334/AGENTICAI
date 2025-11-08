"""Configuration management"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Application configuration"""
    
    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Paths
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    PAPERS_DIR: str = os.path.join(DATA_DIR, "papers")
    CACHE_DIR: str = os.path.join(DATA_DIR, "cache")
    VECTOR_STORE_DIR: str = os.path.join(DATA_DIR, "vector_store")
    
    # Search settings
    DEFAULT_MAX_PAPERS: int = int(os.getenv("DEFAULT_MAX_PAPERS", "10"))
    
    # Processing settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        return True
    
    @classmethod
    def get_model_params(cls) -> dict:
        """Get model parameters"""
        return {
            "model": cls.OPENAI_MODEL,
            "temperature": cls.OPENAI_TEMPERATURE,
            "api_key": cls.OPENAI_API_KEY
        }

