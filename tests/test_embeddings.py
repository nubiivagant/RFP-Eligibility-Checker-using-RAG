import asyncio
from pathlib import Path
from backend.services.parser import DocumentParser
import logging

async def test_embeddings():
    parser = DocumentParser()
    
    # Print initial collection info
    print("Initial collection info:")
    print(parser.get_collection_info())
    
    # Test with a sample PDF
    test_file_path = Path(__file__).parent / "sample.pdf"
    if not test_file_path.exists():
        raise FileNotFoundError("Please place a sample.pdf file in the tests directory")
    
    with open(test_file_path, "rb") as f:
        content = f.read()
    
    # Process document
    result = await parser.process_document(
        content=content,
        doc_type="test",
        doc_id="test_embeddings_001"
    )
    
    # Print final collection info
    print("\nFinal collection info:")
    print(parser.get_collection_info())
    
    # Test querying
    query_results = parser.collection.query(
        query_texts=["test query"],
        n_results=2
    )
    print("\nQuery results:", query_results)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_embeddings())
