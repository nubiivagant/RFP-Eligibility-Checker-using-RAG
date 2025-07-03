import sys
import os
from pathlib import Path
import pytest
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from backend.core.configure import get_report_config

def test_report_config():
    """Test report configuration settings"""
    config = get_report_config()
    
    # Test paths
    assert os.path.exists(config.reports_dir), "Reports directory doesn't exist"
    assert os.path.exists(config.templates_dir), "Templates directory doesn't exist"
    
    # Test URL generation
    test_token = "test123"
    share_url = config.get_share_url(test_token)
    download_url = config.get_download_url(test_token)
    assert share_url.startswith(config.share_base_url), "Invalid share URL"
    assert download_url.startswith(config.share_base_url), "Invalid download URL"
    
    # Test file path generation
    test_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    report_path = config.get_report_path(test_filename)
    assert isinstance(report_path, Path), "Invalid path type"
    assert str(report_path).endswith(".pdf"), "Invalid file extension"
    
    print("\n=== Configuration Test Results ===")
    print(f"Reports Directory: {config.reports_dir}")
    print(f"Templates Directory: {config.templates_dir}")
    print(f"Sample Share URL: {share_url}")
    print(f"Sample Download URL: {download_url}")
    print(f"Sample Report Path: {report_path}")
    print("All tests passed successfully!")

if __name__ == "__main__":
    test_report_config()
