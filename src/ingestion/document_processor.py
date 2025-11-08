"""Document processing and text extraction"""
from pathlib import Path
from typing import List, Dict, Optional
import logging
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents and create vector embeddings"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.embeddings = OpenAIEmbeddings()
        self.vector_store: Optional[FAISS] = None
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        try:
            reader = PdfReader(str(pdf_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def process_papers(self, papers: List[Dict]) -> List[Document]:
        """
        Process papers and create document chunks
        
        Args:
            papers: List of paper metadata dictionaries
            
        Returns:
            List of Document objects with chunks
        """
        documents = []
        
        for paper in papers:
            # Create document from abstract (always available)
            doc_text = f"Title: {paper['title']}\n\n"
            doc_text += f"Authors: {', '.join(paper['authors'])}\n\n"
            doc_text += f"Abstract: {paper['abstract']}\n\n"
            
            # Add any additional content if available
            if 'content' in paper and paper['content']:
                doc_text += f"Content: {paper['content']}\n"
            
            metadata = {
                "title": paper['title'],
                "authors": ", ".join(paper['authors']),
                "arxiv_id": paper.get('arxiv_id', 'unknown'),
                "published": paper.get('published', 'unknown'),
                "source": "arxiv"
            }
            
            doc = Document(page_content=doc_text, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """
        Create a FAISS vector store from documents
        
        Args:
            documents: List of Document objects
            
        Returns:
            FAISS vector store
        """
        logger.info(f"Creating vector store from {len(documents)} documents")
        
        # Split documents into chunks
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Create vector store
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        return self.vector_store
    
    def search_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant document chunks
        """
        if self.vector_store is None:
            logger.warning("Vector store not initialized")
            return []
        
        results = self.vector_store.similarity_search(query, k=k)
        return results
    
    def save_vector_store(self, path: str = "data/vector_store"):
        """Save the vector store to disk"""
        if self.vector_store:
            Path(path).mkdir(parents=True, exist_ok=True)
            self.vector_store.save_local(path)
            logger.info(f"Vector store saved to {path}")
    
    def load_vector_store(self, path: str = "data/vector_store"):
        """Load the vector store from disk"""
        try:
            self.vector_store = FAISS.load_local(
                path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"Vector store loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")

