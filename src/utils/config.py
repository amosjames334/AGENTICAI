"""Configuration management"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Application configuration"""
    
    # Anthropic Claude settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    ANTHROPIC_TEMPERATURE: float = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
    
    # Brave Search MCP settings
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    
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
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return True
    
    @classmethod
    def has_brave_search(cls) -> bool:
        """Whether Brave Search MCP can be enabled"""
        return bool(cls.BRAVE_API_KEY)
    
    @classmethod
    def get_model_params(cls) -> dict:
        """Get model parameters"""
        return {
            "model": cls.ANTHROPIC_MODEL,
            "temperature": cls.ANTHROPIC_TEMPERATURE,
            "api_key": cls.ANTHROPIC_API_KEY
        }
