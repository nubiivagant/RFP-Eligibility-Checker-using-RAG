from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class ReportConfig(BaseSettings):
    # Base directories with absolute paths
    reports_dir: str = os.path.abspath(os.path.join("backend", "reports"))
    templates_dir: str = os.path.abspath(os.path.join("backend", "templates"))
    
    # Download settings
    download_chunk_size: int = 1024 * 1024  # 1MB chunks
    max_report_size: int = 50 * 1024 * 1024  # 50MB limit
    allowed_extensions: list = [".pdf"]
    
    # Share settings
    share_base_url: str = "http://localhost:8000"
    share_token_expiry: int = 24 * 60 * 60  # 24 hours in seconds
    share_token_length: int = 32
    
    # Storage settings
    cleanup_interval: int = 24  # hours
    storage_limit: int = 100 * 1024 * 1024  # 100MB total storage
    
    # PDF Generation
    pdf_options: dict = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'enable-local-file-access': None
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist with proper permissions
        for directory in [self.reports_dir, self.templates_dir]:
            os.makedirs(directory, exist_ok=True)
            os.chmod(directory, 0o777)  # Full permissions

    def get_report_path(self, report_id: str, format: str = None) -> str:
        """Get report file path with better error handling"""
        try:
            # Strip extensions
            report_id = report_id.split('.')[0]
            
            # Check both subdirectory and direct file
            possible_locations = [
                os.path.join(self.reports_dir, report_id, f"{report_id}.{format or 'json'}"),
                os.path.join(self.reports_dir, f"{report_id}.{format or 'json'}")
            ]
            
            for path in possible_locations:
                if os.path.exists(path):
                    return path
                    
            raise FileNotFoundError(f"No report found for ID: {report_id}")
            
        except Exception as e:
            logger.error(f"Failed to get report path: {str(e)}")
            raise FileNotFoundError(f"No report found for ID: {report_id}")

    def generate_share_link(self, report_id: str) -> str:
        """Generate a shareable link for the report"""
        base_url = self.share_base_url.rstrip('/')
        return f"{base_url}/view-report/{report_id}"

    def get_report_type(self, report_id: str) -> str:
        """Get report file type"""
        if os.path.exists(os.path.join(self.reports_dir, f"{report_id}.pdf")):
            return "application/pdf"
        elif os.path.exists(os.path.join(self.reports_dir, f"{report_id}.json")):
            return "application/json"
        return None
    
    def get_share_url(self, token: str) -> str:
        """Generate shareable URL for a report"""
        return f"{self.share_base_url}/api/reports/share/{token}"
    
    def get_download_url(self, token: str) -> str:
        """Generate download URL for a report"""
        return f"{self.share_base_url}/api/reports/download/{token}"

@lru_cache()
def get_report_config() -> ReportConfig:
    """Get cached report configuration"""
    try:
        config = ReportConfig()
        logger.info("Report configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}", exc_info=True)
        raise
