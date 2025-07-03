import sys, os
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
import logging
import json
import time
import asyncio
from werkzeug.utils import secure_filename
import traceback
import atexit
import shutil
from datetime import datetime
from werkzeug.serving import run_simple

# Configure logging properly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Update path handling
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

# Import services first
from backend.services.comparison_service import DocumentComparison
from backend.services.report import ReportGenerator
from backend.core.configure import get_report_config

# Initialize event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

def init_services():
    """Initialize all required services"""
    try:
        logger.info("Initializing services...")
        
        # Create necessary directories
        chromadb_path = os.path.join("backend", "data", "chromadb")
        reports_dir = os.path.join("backend", "reports")
        for path in [chromadb_path, reports_dir]:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)
            
        config = get_report_config()
        doc_comparison = DocumentComparison()
        report_generator = ReportGenerator()
        
        # Test connection
        test_result = doc_comparison.parser.test_embedding()
        if test_result["status"] != "success":
            raise Exception("Embedding test failed")
            
        logger.info("Services initialized successfully")
        return config, doc_comparison, report_generator
    except Exception as e:
        logger.error(f"Service initialization failed: {str(e)}")
        raise

# Initialize services
config, doc_comparison, report_generator = init_services()

# Initialize services with proper cleanup
def cleanup_resources():
    """Cleanup function to be called on exit"""
    try:
        if 'doc_comparison' in globals():
            doc_comparison._cleanup()
        if 'loop' in globals():
            loop.close()
    except Exception as e:
        print(f"Cleanup failed: {str(e)}")

# Register cleanup function
atexit.register(cleanup_resources)

# Configure app
app = Flask(__name__,
    template_folder=os.path.join(backend_dir, 'templates'),
    static_folder=os.path.join('frontend', 'static')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
async def upload_documents():
    try:
        if 'rfp_document' not in request.files or 'company_document' not in request.files:
            return jsonify({"error": "Both files are required"}), 400

        rfp_file = request.files['rfp_document']
        company_file = request.files['company_document']

        # Read binary content
        rfp_content = rfp_file.read()
        company_content = company_file.read()

        # Compare documents
        result = await doc_comparison.compare_documents(
            rfp_content=rfp_content,
            company_content=company_content
        )

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
async def analyze_documents():
    try:
        if 'rfp_document' not in request.files or 'company_document' not in request.files:
            return jsonify({"error": "Missing required files"}), 400

        rfp_file = request.files['rfp_document']
        company_file = request.files['company_document']

        # Read file contents
        rfp_content = rfp_file.read()
        company_content = company_file.read()

        # Create report directory first
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_id = f"rfp_analysis_{timestamp}"
        report_dir = os.path.join(config.reports_dir, report_id)
        os.makedirs(report_dir, exist_ok=True)

        # Generate report paths
        json_path = os.path.join(report_dir, f"{report_id}.json")
        pdf_path = os.path.join(report_dir, f"{report_id}.pdf")

        try:
            logger.info(f"Starting analysis for RFP: {rfp_file.filename}")
            comparison_result = await doc_comparison.compare_documents(
                rfp_content=rfp_content,
                company_content=company_content
            )
            
            eligibility_result = await doc_comparison.get_result(
                rfp_content=rfp_content,
                company_content=company_content
            )

            # Generate report with proper extension and naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_id = f"analysis_{timestamp}"
            
            # Format complete analysis data
            analysis_data = {
                "eligible": eligibility_result["eligible"],
                "rfp_name": rfp_file.filename,
                "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "scores": eligibility_result.get("scores", {
                    "overall_score": 0,
                    "technical_match": 0,
                    "requirement_coverage": 0
                }),
                "conditions": {  # Add conditions for template
                    "has_requirements": len(comparison_result["matches"]) > 0,
                    "technical_match": True if eligibility_result.get("scores", {}).get("technical_match", 0) > 70 else False,
                    "coverage_sufficient": True if eligibility_result.get("scores", {}).get("requirement_coverage", 0) > 75 else False
                },
                "conditions_met": {
                    "has_requirements": len(comparison_result["matches"]) > 0,
                    "has_high_matches": any(1.0 - float(min(m["company_matches"]["distances"])) > 0.8 
                                        for m in comparison_result["matches"]),
                    "requirements_coverage": len(comparison_result["matches"]) / comparison_result["total_chunks_processed"]["rfp"]
                },
                "matching_details": comparison_result.get("matches", []),
                "metrics": comparison_result.get("match_statistics", {}),
                "risks": [],  # Will be populated by report generator
                "checklist": [],  # Will be populated by report generator
                "qualifications": []  # Will be populated by report generator
            }

            # Save JSON data first
            with open(json_path, 'w') as f:
                json.dump(analysis_data, f)

            # Generate report without output_path
            logger.info("Analysis completed, generating report...")
            report_result = report_generator.generate_report(
                analysis_result=analysis_data,
                rfp_name=rfp_file.filename
            )
            
            return jsonify({
                "status": "success",
                "report_id": report_result["report_id"],
                "redirect_url": f"/view-report/{report_result['report_id']}",
                "eligible": analysis_data["eligible"]
            })

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return jsonify({"error": "Analysis failed"}), 500

    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/results/<report_id>')
def get_report(report_id):
    try:
        result = doc_comparison.get_result_by_id(report_id)
        if not result:
            return jsonify({"error": "Report not found"}), 404
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/view-report/<report_id>')
def view_report(report_id):
    try:
        # Always try JSON first since it's guaranteed to exist
        report_id = report_id.split('.')[0]
        json_path = os.path.join(config.reports_dir, report_id, f"{report_id}.json")
        
        if not os.path.exists(json_path):
            return "Report not found", 404
            
        with open(json_path, 'r') as f:
            report_data = json.load(f)

        # Check if PDF exists, otherwise use JSON for download
        pdf_path = os.path.join(config.reports_dir, report_id, f"{report_id}.pdf")
        format_ext = 'pdf' if os.path.exists(pdf_path) else 'json'
            
        # Ensure all required template variables exist
        report_data.update({
            "conditions": report_data.get("conditions", {}),
            "scores": report_data.get("scores", {}),
            "metrics": report_data.get("metrics", {}),
            "risks": report_data.get("risks", []),
            "checklist": report_data.get("checklist", []),
            "qualifications": report_data.get("qualifications", []),
            "report_id": report_id,
            "download_url": f"/download/{report_id}.{format_ext}",
            "share_url": f"/share/{report_id}"
        })
        
        return render_template('report_template.html', **report_data)
        
    except Exception as e:
        logger.error(f"Failed to view report: {str(e)}")
        return str(e), 500

@app.route('/download/<report_id>')
def download_report(report_id):
    try:
        report_id = report_id.split('.')[0]
        
        # Try PDF first, fall back to JSON
        pdf_path = os.path.join(config.reports_dir, report_id, f"{report_id}.pdf")
        if os.path.exists(pdf_path):
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"{report_id}.pdf"
            )
            
        # Fall back to JSON
        json_path = os.path.join(config.reports_dir, report_id, f"{report_id}.json")
        if os.path.exists(json_path):
            return send_file(
                json_path,
                mimetype='application/json',
                as_attachment=True,
                download_name=f"{report_id}.json"
            )
            
        return "Report not found", 404
            
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return str(e), 500

@app.route('/share/<report_id>')
def share_report(report_id):
    try:
        report_id = report_id.split('.')[0]  # Remove extension
        share_url = config.generate_share_link(report_id)
        
        return jsonify({
            "share_url": share_url,
            "report_id": report_id,
            "expires_in": "24 hours"
        })
            
    except Exception as e:
        logger.error(f"Share failed: {str(e)}", exc_info=True)
        return str(e), 500

if __name__ == '__main__':
    try:
        # Ensure clean startup
        os.makedirs(config.reports_dir, exist_ok=True)
        
        print("\nStarting RFP Analysis Tool...")
        print("Server running at http://127.0.0.1:8000")
        print("Press CTRL+C to quit\n")
        
        app.run(
            host='127.0.0.1',
            port=8000,
            debug=True,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
    finally:
        cleanup_resources()
