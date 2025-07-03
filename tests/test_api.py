import httpx
import asyncio
import logging
import time
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_server(client: httpx.AsyncClient) -> bool:
    """Check if server is running"""
    try:
        response = await client.get('http://localhost:8000/health')
        return response.status_code == 200
    except:
        return False

async def wait_for_server(timeout: int = 30) -> bool:
    """Wait for server to be ready"""
    start_time = time.time()
    async with httpx.AsyncClient(timeout=10.0) as client:
        while time.time() - start_time < timeout:
            if await check_server(client):
                return True
            logger.info("Waiting for server to be ready...")
            await asyncio.sleep(2)
        return False

async def test_analysis_api():
    """Test the analysis API endpoints"""
    # Wait for server
    if not await wait_for_server():
        logger.error("Server not available")
        return

    # Test with retry logic
    retries = 3
    while retries > 0:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post('http://localhost:8000/api/test')
                logger.info("Test API Response:")
                logger.info(response.json())
                break
        except Exception as e:
            retries -= 1
            if retries == 0:
                logger.error(f"API test failed after all retries: {str(e)}")
            else:
                logger.warning(f"Attempt failed, retrying... ({retries} left)")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_analysis_api())
