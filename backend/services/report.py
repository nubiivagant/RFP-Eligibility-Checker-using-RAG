import pdfkit
import jinja2
from datetime import datetime
import os
from typing import Dict, Any
import uuid
from urllib.parse import urljoin
import logging
import json
import shutil

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        try:
            # Absolute paths for directories
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.report_dir = os.path.join(self.base_dir, "reports")
            os.makedirs(self.report_dir, exist_ok=True)
            os.chmod(self.report_dir, 0o777)

            self.template_dir = os.path.join(self.base_dir, "templates")
            os.makedirs(self.template_dir, exist_ok=True)
            
            self.template_loader = jinja2.FileSystemLoader(searchpath=self.template_dir)
            self.template_env = jinja2.Environment(loader=self.template_loader)
            
            # Try multiple wkhtmltopdf paths
            wkhtmltopdf_paths = [
                r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
                "/usr/local/bin/wkhtmltopdf",
                "/usr/bin/wkhtmltopdf",
                "wkhtmltopdf"  # Try PATH
            ]
            
            self.wkhtmltopdf_path = None
            for path in wkhtmltopdf_paths:
                try:
                    if shutil.which(path):
                        self.wkhtmltopdf_path = path
                        break
                except:
                    continue

            self.pdf_config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path) if self.wkhtmltopdf_path else None
            
        except Exception as e:
            logger.error(f"ReportGenerator initialization failed: {str(e)}")
            raise

        # Configure pdfkit options
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        self.base_url = "http://localhost:8000"  # Update with your domain
        self.share_tokens = {}

    def _extract_qualifications(self, analysis_result: Dict[str, Any]) -> list:
        """Extract and analyze required qualifications"""
        qualifications = []
        matches = analysis_result.get("matches", [])
        
        # Keywords to identify different types of requirements
        requirement_patterns = {
            "Certification": ["certif", "license", "accredit"],
            "Experience": ["experience", "year", "background"],
            "Technical": ["technical", "skill", "proficiency"],
            "Education": ["degree", "education", "qualification"],
            "Compliance": ["comply", "standard", "regulation"]
        }

        for match in matches:
            text = match["rfp_text"].lower()
            score = 1.0 - float(min(match["company_matches"]["distances"]))
            
            for req_type, keywords in requirement_patterns.items():
                if any(keyword in text for keyword in keywords):
                    qualifications.append({
                        "type": req_type,
                        "details": match["rfp_text"],
                        "met": score > 0.8
                    })
                    break

        return qualifications

    def generate_report(self, analysis_result: Dict[str, Any], rfp_name: str) -> Dict[str, Any]:
        """Generate report with JSON fallback"""
        try:
            logger.info(f"Generating report for {rfp_name}")
            
            # Ensure required fields exist in analysis_result
            analysis_result.update({
                "scores": analysis_result.get("scores", {
                    "overall_score": 0,
                    "technical_match": 0,
                    "requirement_coverage": 0
                }),
                "conditions_met": analysis_result.get("conditions_met", {}),
                "metrics": analysis_result.get("metrics", {}),
                "risks": self._analyze_risks(analysis_result),
                "checklist": self._generate_checklist(analysis_result),
                "qualifications": self._extract_qualifications(analysis_result),
                "matching_details": analysis_result.get("matching_details", {})
            })
            
            # Generate report ID and paths
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_id = f"rfp_analysis_{timestamp}"
            report_dir = os.path.join(self.report_dir, report_id)
            os.makedirs(report_dir, exist_ok=True)
            
            # Generate paths
            json_path = os.path.join(report_dir, f"{report_id}.json")
            pdf_path = os.path.join(report_dir, f"{report_id}.pdf")

            # Save JSON
            with open(json_path, 'w') as f:
                json.dump(analysis_result, f)

            # Try PDF generation
            if self.pdf_config:
                try:
                    template = self.template_env.get_template('report_template.html')
                    html_content = template.render(**analysis_result)
                    pdfkit.from_string(html_content, pdf_path, configuration=self.pdf_config)
                except Exception as e:
                    logger.warning(f"PDF generation failed: {str(e)}")
                    pdf_path = None

            return {
                "report_id": report_id,
                "format": "pdf" if pdf_path and os.path.exists(pdf_path) else "json",
                "path": pdf_path if pdf_path and os.path.exists(pdf_path) else json_path
            }

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            raise

    def _analyze_risks(self, analysis_result: Dict[str, Any]) -> list:
        """Generate detailed risk analysis"""
        risks = []
        scores = analysis_result.get("scores", {})
        metrics = analysis_result.get("metrics", {})

        if scores.get("overall_score", 0) < 75:
            risks.append("High Risk: Overall match score below minimum threshold (75%)")
        
        if scores.get("requirement_coverage", 0) < 80:
            risks.append(f"High Risk: Only {scores.get('requirement_coverage')}% of requirements covered (minimum 80%)")
        
        if metrics.get("high_confidence_matches", 0) / max(metrics.get("total_requirements", 1), 1) < 0.6:
            risks.append("Medium Risk: Low number of high-confidence requirement matches")
        
        return risks

    def _generate_checklist(self, analysis_result: Dict[str, Any]) -> list:
        """Generate submission checklist based on analysis"""
        checklist = [
            "Complete all mandatory fields in RFP response template",
            "Attach company credentials and certifications",
            "Include detailed technical approach",
            "Provide project timeline and milestones",
            "Include cost breakdown and pricing details",
            "Attach relevant past performance examples",
            "Include required forms and certifications",
            "Prepare executive summary"
        ]
        
        # Safely check conditions with default values
        conditions = analysis_result.get('conditions_met', {})
        if not conditions.get('has_high_matches', False):
            checklist.append("Strengthen technical capabilities documentation")
        if not conditions.get('majority_matched', False):
            checklist.append("Address gaps in requirements coverage")
        
        return checklist

    def get_report_link(self, filepath: str) -> str:
        """Generate shareable link for report"""
        # In a real implementation, this would upload to cloud storage
        # and return a shareable link
        return f"file://{filepath}"

    def get_report_by_id(self, report_id: str) -> str:
        """Get report filepath by ID"""
        return self.share_tokens.get(report_id)

    def cleanup_old_reports(self, max_age_hours: int = 24):
        """Clean up old report files"""
        current_time = datetime.now()
        for filename in os.listdir(self.report_dir):
            filepath = os.path.join(self.report_dir, filename)
            file_age = (current_time - datetime.fromtimestamp(os.path.getctime(filepath))).total_seconds() / 3600
            if file_age > max_age_hours:
                os.remove(filepath)
        
        # Also cleanup old share tokens
        expired_tokens = [token for token, path in self.share_tokens.items() 
                         if not os.path.exists(path)]
        for token in expired_tokens:
            self.share_tokens.pop(token, None)

    def test_report_generation(self):
        """Test report generation with sample data"""
        sample_analysis = {
            "eligible": True,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "rfp_name": "Test RFP",
            "conditions_met": {
                "has_requirements": True,
                "has_high_matches": True,
                "more_high_than_low": True,
                "majority_matched": True
            }
        }
        
        try:
            result = self.generate_report(
                analysis_result=sample_analysis,
                rfp_name="ELIGIBLE RFP -1.pdf"
            )
            
            # Check if we got a valid result with path
            if result and result.get("path") and os.path.exists(result["path"]):
                print(f"Test report generated successfully at: {result['path']}")
                return True
                
            return False
        except Exception as e:
            print(f"Report generation test failed: {str(e)}")
            return False

if __name__ == "__main__":
    # Quick test
    generator = ReportGenerator()
    generator.test_report_generation()
