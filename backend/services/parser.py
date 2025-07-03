from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.docstore.document import Document
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import os, shutil, time
from pathlib import Path
import logging
from typing import Dict, Any, Union, List
import tempfile
import io
from PyPDF2 import PdfReader
from docx import Document
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentParser:
    def __init__(self):
        try:
            self.db_path = os.path.join("backend", "data", "chromadb")
            # Initialize embedding function first
            self.embedding_function = DefaultEmbeddingFunction()
            
            # Force clean start
            if os.path.exists(self.db_path):
                shutil.rmtree(self.db_path, ignore_errors=True)
                time.sleep(1)  # Wait for cleanup
            os.makedirs(self.db_path, exist_ok=True)

            # Initialize with unique collection name
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.collection_name = f"documents_{int(time.time())}"
            self._initialize_collection()
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {str(e)}")
            raise

        self.base_path = Path(__file__).parent.parent
        self.docs_path = self.base_path / "data" / "documents"
        self.chromadb_path = self.base_path / "data" / "chromadb"
        
        # Create necessary directories
        self.docs_path.mkdir(parents=True, exist_ok=True)
        self.chromadb_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize tools
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        # Ensure ChromaDB initialization
        self._initialize_chromadb()

    def _initialize_collection(self):
        """Initialize collection with unique name"""
        try:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"created": time.strftime("%Y-%m-%d %H:%M:%S")},
                embedding_function=self.embedding_function
            )
        except Exception as e:
            logger.error(f"Collection initialization failed: {str(e)}")
            raise

    def _initialize_chromadb(self):
        """Initialize ChromaDB with proper settings"""
        logger.info("Initializing ChromaDB...")
        
        try:
            # Safely remove existing data with retries
            if self.chromadb_path.exists():
                logger.info("Cleaning existing ChromaDB data")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self._safe_cleanup()
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(1)
            
            self.chromadb_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB with settings
            self.db = chromadb.PersistentClient(
                path=str(self.chromadb_path),
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create collection with simplified metadata
            self.collection = self.db.create_collection(
                name="documents",
                metadata={"space": "cosine"}
            )
            
            logger.info(f"ChromaDB initialized at {self.chromadb_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    def _safe_cleanup(self):
        """Safely cleanup resources"""
        try:
            if hasattr(self, 'collection'):
                self.client.delete_collection("documents")
        except:
            pass

    def _split_pdf(self, content: bytes) -> List[str]:
        """Improved PDF splitting with better error handling"""
        try:
            text = ""
            # Try PyMuPDF first
            try:
                with fitz.open(stream=content, filetype="pdf") as doc:
                    for page in doc:
                        text += page.get_text()
            except Exception as e:
                logger.warning(f"PyMuPDF failed, trying PyPDF2: {str(e)}")
                # Fallback to PyPDF2
                pdf = PdfReader(io.BytesIO(content))
                for page in pdf.pages:
                    text += page.extract_text()

            if not text.strip():
                raise ValueError("No text content extracted from PDF")

            # Split into chunks with overlap
            chunks = self.text_splitter.split_text(text)
            if not chunks:
                raise ValueError("No valid chunks extracted")

            return chunks

        except Exception as e:
            logger.error(f"PDF splitting failed: {str(e)}")
            raise

    def _split_docx(self, content: bytes) -> List[str]:
        """Split DOCX content into text chunks"""
        try:
            doc = Document(io.BytesIO(content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            chunks = self.text_splitter.split_text(text)
            return chunks
        except Exception as e:
            logger.error(f"DOCX splitting failed: {str(e)}")
            raise

    async def process_document(self, content: bytes, doc_type: str, doc_id: str) -> Dict[str, Any]:
        """Process document content with better error handling"""
        try:
            # Generate unique IDs with timestamp
            timestamp = int(time.time() * 1000)
            chunks = self._split_pdf(content)
            
            # Add chunks in batches to avoid conflicts
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_ids = [f"{doc_type}_{timestamp}_{j}" for j in range(i, i + len(batch_chunks))]
                batch_metadata = [{
                    "doc_type": doc_type,
                    "doc_id": doc_id,
                    "chunk_id": j,
                    "total_chunks": len(chunks)
                } for j in range(i, i + len(batch_chunks))]
                
                try:
                    self.collection.add(
                        documents=batch_chunks,
                        metadatas=batch_metadata,
                        ids=batch_ids
                    )
                except Exception as e:
                    logger.error(f"Failed to add batch {i}: {str(e)}")
                    continue

            return {
                "texts": chunks,
                "doc_type": doc_type,
                "doc_id": doc_id,
                "chunk_count": len(chunks)
            }

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise

    async def process_document(self, content: bytes, doc_type: str, doc_id: str) -> Dict[str, Any]:
        """Process document content and store in ChromaDB"""
        try:
            # Determine file type and process accordingly
            try:
                # Try PDF first
                text_chunks = self._split_pdf(content)
            except:
                try:
                    # Try DOCX if PDF fails
                    text_chunks = self._split_docx(content)
                except Exception as e:
                    logger.error(f"Document processing failed: {str(e)}")
                    raise

            # Store in ChromaDB
            if text_chunks:
                self.collection.add(
                    documents=text_chunks,
                    metadatas=[{"doc_type": doc_type, "chunk_id": i} for i in range(len(text_chunks))],
                    ids=[f"{doc_id}_{i}" for i in range(len(text_chunks))]
                )

            return {
                "texts": text_chunks,
                "doc_type": doc_type,
                "doc_id": doc_id
            }
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise

    def verify_storage(self, doc_id: str, expected_chunks: int):
        """Verify document storage in ChromaDB"""
        try:
            # Query for the document chunks
            results = self.collection.get(
                where={"doc_id": doc_id}
            )
            actual_chunks = len(results['ids'])
            logger.info(f"Verification - Expected chunks: {expected_chunks}, Found: {actual_chunks}")
            
            if actual_chunks != expected_chunks:
                logger.warning(f"Chunk count mismatch for doc_id {doc_id}")
            
            return actual_chunks == expected_chunks
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return False

    def get_collection_info(self):
        """Get information about the current collection"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "location": str(self.chromadb_path)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None

    def clean_storage(self):
        """Clean up storage directories"""
        shutil.rmtree(self.docs_path, ignore_errors=True)
        shutil.rmtree(self.chromadb_path, ignore_errors=True)
        self.docs_path.mkdir(parents=True, exist_ok=True)
        self.chromadb_path.mkdir(parents=True, exist_ok=True)

    def test_embedding(self, sample_text: str = "This is a test document."):
        """Test embedding functionality directly in the parser"""
        try:
            # Add test document
            self.collection.add(
                documents=[sample_text],
                metadatas=[{"type": "test"}],
                ids=["test_1"]
            )
            
            # Query to verify
            results = self.collection.query(
                query_texts=[sample_text],
                n_results=1
            )
            
            logger.info("Test Results:")
            logger.info(f"Documents in collection: {self.collection.count()}")
            logger.info(f"Query results: {results}")
            
            return {
                "status": "success",
                "collection_count": self.collection.count(),
                "query_results": results
            }
            
        except Exception as e:
            logger.error(f"Embedding test failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_document_embeddings(self, doc_type: str):
        """Retrieve embeddings for a specific document type"""
        try:
            results = self.collection.get(
                where={"doc_type": doc_type}
            )
            return results
        except Exception as e:
            logger.error(f"Failed to get embeddings for {doc_type}: {str(e)}")
            return None

    async def compare_embeddings(self, query_embedding, target_embeddings):
        """Compare embeddings and return similarity scores"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                where={"doc_type": "company"},
                n_results=2
            )
            return results
        except Exception as e:
            logger.error(f"Embedding comparison failed: {str(e)}")
            return None

if __name__ == "__main__":
    try:
        parser = DocumentParser()
        test_result = parser.test_embedding()
        print(f"\nTest completed with result: {test_result}")
    except Exception as e:
        print(f"Failed to initialize or test parser: {str(e)}")
