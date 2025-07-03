import os
import sys
from datetime import datetime

backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.append(backend_dir)

from services.report import ReportGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        generator = ReportGenerator()
        
        # Real RFP test data
        test_analysis = {
            "eligible": True,
            "conditions_met": {
                "has_requirements": True,
                "has_high_matches": True,
                "more_high_than_low": True,
                "majority_matched": True
            },
            "matching_details": {
                "requirements": [
                    "Python Development Experience",
                    "Cloud Infrastructure",
                    "Database Management",
                    "API Development",
                    "Security Compliance"
                ],
                "matched_capabilities": [
                    "8 years Python development",
                    "AWS and Azure certified team",
                    "PostgreSQL and MongoDB expertise",
                    "RESTful API development",
                    "ISO 27001 certified"
                ]
            },
            "scores": {
                "technical_match": 0.92,
                "experience_match": 0.85,
                "compliance_match": 0.88
            }
        }
        
        # Generate report for ELIGIBLE RFP-1
        report_path = generator.generate_report(
            analysis_result=test_analysis,
            rfp_name="ELIGIBLE RFP-1.pdf"
        )
        
        if os.path.exists(report_path):
            logger.info("\n=== Report Generation Success ===")
            logger.info(f"RFP Document: ELIGIBLE RFP-1.pdf")
            logger.info(f"Report Location: {report_path}")
            logger.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"File Size: {os.path.getsize(report_path):,} bytes")
            logger.info("\nReport Link: " + generator.get_report_link(report_path))
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        return False

if __name__ == "__main__":
    main()
