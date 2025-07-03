import uuid
from pathlib import Path
from typing import Union

def generate_document_id() -> str:
    """Generate a unique document ID"""
    return str(uuid.uuid4())

def ensure_directory(path: Union[str, Path]):
    """Ensure a directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower()
