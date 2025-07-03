import httpx
import asyncio
from pathlib import Path

async def test_comparison():
    # Test files
    test_dir = Path(__file__).parent / "test_files"
    rfp_file = test_dir / "sample_rfp.pdf"
    company_file = test_dir / "sample_company.pdf"
    
    if not all([rfp_file.exists(), company_file.exists()]):
        print("Please ensure test PDF files exist in tests/test_files directory")
        return
    
    # Prepare files for upload
    files = {
        'rfp_document': ('rfp.pdf', open(rfp_file, 'rb'), 'application/pdf'),
        'company_document': ('company.pdf', open(company_file, 'rb'), 'application/pdf')
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'http://localhost:8000/api/compare',
                files=files
            )
            
            print("Status Code:", response.status_code)
            print("Response:", response.json())
            
    except Exception as e:
        print(f"Error during comparison test: {str(e)}")
    
    finally:
        # Clean up
        for file_obj in files.values():
            file_obj[1].close()

if __name__ == "__main__":
    asyncio.run(test_comparison())
