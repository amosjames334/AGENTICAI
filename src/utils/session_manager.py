"""Session manager for organizing research projects"""
from pathlib import Path
import re
import hashlib
from typing import Optional
import json
from datetime import datetime


def slugify(text: str, max_len: int = 50) -> str:
    """Convert text to safe folder name"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    text = text.strip('_')
    return text[:max_len] if text else "default"


def generate_session_id(topic: str) -> str:
    """Generate unique session ID from topic"""
    hash_suffix = hashlib.md5(topic.encode()).hexdigest()[:8]
    slug = slugify(topic, max_len=40)
    return f"{slug}_{hash_suffix}"


class SessionManager:
    """
    Manages research sessions with topic-based folder organization
    
    Directory structure:
    data/
    └── sessions/
        └── {session_id}/
            ├── papers/          # Downloaded PDFs
            ├── vector_store/    # FAISS index
            ├── cache/           # Temporary files
            └── session.json     # Session metadata
    """
    
    def __init__(self, base_dir: str = "data", session_id: Optional[str] = None):
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id = session_id
        self.session_dir = None
        self.papers_dir = None
        self.vector_store_dir = None
        self.cache_dir = None
        self.metadata = {}
        
        if session_id:
            self._load_or_create_session(session_id)
    
    def create_session(self, topic: str, description: str = "") -> str:
        """
        Create a new research session
        
        Args:
            topic: Research topic
            description: Optional description
            
        Returns:
            Session ID
        """
        session_id = generate_session_id(topic)
        self.session_id = session_id
        self._load_or_create_session(session_id, topic, description)
        return session_id
    
    def _load_or_create_session(self, session_id: str, topic: str = "", description: str = ""):
        """Load existing session or create new one"""
        self.session_dir = self.sessions_dir / session_id
        self.papers_dir = self.session_dir / "papers"
        self.vector_store_dir = self.session_dir / "vector_store"
        self.cache_dir = self.session_dir / "cache"
        
        # Create directories
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create metadata
        metadata_file = self.session_dir / "session.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "session_id": session_id,
                "topic": topic,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "papers_count": 0,
                "chunks_count": 0
            }
            self._save_metadata()
    
    def _save_metadata(self):
        """Save session metadata"""
        self.metadata["updated_at"] = datetime.now().isoformat()
        metadata_file = self.session_dir / "session.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def update_metadata(self, **kwargs):
        """Update session metadata"""
        self.metadata.update(kwargs)
        self._save_metadata()
    
    def get_papers_dir(self) -> str:
        """Get papers directory path"""
        return str(self.papers_dir)
    
    def get_vector_store_dir(self) -> str:
        """Get vector store directory path"""
        return str(self.vector_store_dir)
    
    def get_cache_dir(self) -> str:
        """Get cache directory path"""
        return str(self.cache_dir)

    RESULTS_FILE = "results.json"

    def save_results(self, results: dict) -> None:
        """Persist the latest agent-analysis run for this session.

        The bulky `papers` list is stripped (it is restored from manifest.json).
        Best-effort: never raises so a save failure cannot break a run.
        """
        if not self.session_dir:
            return
        try:
            to_save = {k: v for k, v in results.items() if k != "papers"}
            to_save["run_at"] = datetime.now().isoformat()
            results_file = self.session_dir / self.RESULTS_FILE
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2)
        except Exception:
            # Persistence is best-effort; ignore failures.
            pass

    def load_results(self) -> Optional[dict]:
        """Load the saved run results for this session, if any."""
        if not self.session_dir:
            return None
        results_file = self.session_dir / self.RESULTS_FILE
        if not results_file.exists():
            return None
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def has_results(self) -> bool:
        """Whether a saved run exists for this session."""
        if not self.session_dir:
            return False
        return (self.session_dir / self.RESULTS_FILE).exists()
    
    @staticmethod
    def list_sessions(base_dir: str = "data") -> list:
        """
        List all available sessions
        
        Returns:
            List of session metadata dictionaries
        """
        sessions_dir = Path(base_dir) / "sessions"
        if not sessions_dir.exists():
            return []
        
        sessions = []
        for session_path in sessions_dir.iterdir():
            if session_path.is_dir():
                metadata_file = session_path / "session.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        sessions.append(json.load(f))
        
        # Sort by updated_at (newest first)
        sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return sessions
    
    @staticmethod
    def load_session(session_id: str, base_dir: str = "data") -> 'SessionManager':
        """Load an existing session"""
        manager = SessionManager(base_dir=base_dir, session_id=session_id)
        return manager
    
    def delete_session(self):
        """Delete current session and all its data"""
        if self.session_dir and self.session_dir.exists():
            import shutil
            shutil.rmtree(self.session_dir)
    
    def get_session_info(self) -> dict:
        """Get session information"""
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "papers_dir": str(self.papers_dir),
            "vector_store_dir": str(self.vector_store_dir),
            "cache_dir": str(self.cache_dir),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"SessionManager(session_id='{self.session_id}', topic='{self.metadata.get('topic', 'Unknown')}')"

