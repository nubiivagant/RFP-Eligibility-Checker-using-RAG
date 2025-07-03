import numpy as np
from pathlib import Path
import logging
import sys, os
from typing import Dict, List, Any, Union
from groq import Groq
from dotenv import load_dotenv

# Fix imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.parser import DocumentParser

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentComparison:
    def __init__(self):
        try:
            self.parser = DocumentParser()
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("GROQ_API_KEY not found, using distance-based matching only")
                self.groq_client = None
            else:
                self.groq_client = Groq(api_key=api_key)
                
                self.model = "llama2-70b-4096"
            logger.info("DocumentComparison initialized successfully")
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise

    def _cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'parser'):
            try:
                self.parser._safe_cleanup()
            except:
                pass

    async def compare_documents(self, rfp_content: bytes, company_content: bytes) -> Dict[str, Any]:
        """Compare RFP document with company document"""
        try:
            # Add debug logging
            logger.info("Starting document comparison")
            logger.info(f"RFP content size: {len(rfp_content)} bytes")
            logger.info(f"Company content size: {len(company_content)} bytes")

            # Process documents with better error handling
            try:
                rfp_result = await self.parser.process_document(content=rfp_content, doc_type="rfp", doc_id="rfp_current")
                company_result = await self.parser.process_document(content=company_content, doc_type="company", doc_id="company_current")
            except Exception as e:
                logger.error(f"Document processing failed: {str(e)}")
                raise

            # Improve matching logic with better similarity calculation
            matches = []
            for idx, rfp_chunk in enumerate(rfp_result["texts"]):
                try:
                    results = self.parser.collection.query(
                        query_texts=[rfp_chunk],
                        where={"doc_type": "company"},
                        n_results=3  # Get top 3 matches for better accuracy
                    )
                    
                    # Normalize distances to ensure positive scores
                    distances = [min(1.0, max(0.0, float(d))) for d in results["distances"][0]]
                    best_distance = min(distances)
                    
                    matches.append({
                        "rfp_text": rfp_chunk,
                        "company_matches": {
                            "texts": results["documents"][0],
                            "distances": distances,
                            "best_match_score": 1.0 - best_distance,
                            "metadata": results["metadatas"][0]
                        }
                    })
                except Exception as e:
                    logger.warning(f"Failed to process chunk {idx}: {str(e)}")
                    continue

            return {
                "matches": matches,
                "total_chunks_processed": {
                    "rfp": len(rfp_result["texts"]),
                    "company": len(company_result["texts"])
                },
                "match_statistics": self._calculate_match_statistics(matches)
            }

        except Exception as e:
            logger.error(f"Comparison failed: {str(e)}", exc_info=True)
            raise

    def _calculate_similarity(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed similarity metrics with improved accuracy"""
        try:
            if not matches:
                return {
                    "eligible": False,
                    "scores": {
                        "technical_match": 0,
                        "requirement_coverage": 0,
                        "overall_score": 0
                    },
                    "metrics": {
                        "matched_requirements": 0,
                        "total_requirements": 0,
                        "high_confidence_matches": 0
                    }
                }

            total_reqs = len(matches)
            scores = []
            high_confidence = 0
            matched_reqs = 0

            for match in matches:
                try:
                    # Get the best match score
                    distance = float(min(match["company_matches"]["distances"]))
                    # Convert distance to similarity (ensure positive score)
                    similarity = max(0, min(100, (1.0 - distance) * 100))
                    scores.append(similarity)

                    # Adjust thresholds for better accuracy
                    if similarity >= 80:  # High confidence threshold
                        high_confidence += 1
                        matched_reqs += 1
                    elif similarity >= 60:  # Medium confidence threshold
                        matched_reqs += 1

                except Exception as e:
                    logger.warning(f"Failed to process match score: {str(e)}")
                    continue

            # Calculate scores with proper bounds
            technical_match = sum(scores) / total_reqs if scores else 0
            requirement_coverage = (matched_reqs / total_reqs * 100) if total_reqs > 0 else 0
            
            # Calculate weighted overall score
            weight_technical = 0.6
            weight_coverage = 0.4
            overall_score = (
                technical_match * weight_technical + 
                requirement_coverage * weight_coverage
            )

            # Determine eligibility with adjusted thresholds
            is_eligible = (
                overall_score >= 70 and  # Reduced threshold
                requirement_coverage >= 75 and  # Adjusted coverage requirement
                (high_confidence / total_reqs) >= 0.5  # Adjusted confidence threshold
            )

            return {
                "eligible": is_eligible,
                "scores": {
                    "technical_match": round(technical_match, 2),
                    "requirement_coverage": round(requirement_coverage, 2),
                    "overall_score": round(overall_score, 2)
                },
                "metrics": {
                    "matched_requirements": matched_reqs,
                    "total_requirements": total_reqs,
                    "high_confidence_matches": high_confidence
                }
            }

        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return {"eligible": False, "scores": {}, "metrics": {}}

    def _calculate_match_statistics(self, matches: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed match statistics"""
        try:
            if not matches:
                return {"error": "No matches found"}

            scores = [m["company_matches"]["best_match_score"] for m in matches]
            
            return {
                "avg_score": sum(scores) / len(scores),
                "high_confidence": sum(1 for s in scores if s > 0.8),
                "medium_confidence": sum(1 for s in scores if 0.6 <= s <= 0.8),
                "low_confidence": sum(1 for s in scores if s < 0.6),
                "total_matches": len(matches)
            }
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {str(e)}")
            return {"error": str(e)}

    async def get_result(self, rfp_content: bytes, company_content: bytes) -> Dict[str, Any]:
        """Get detailed eligibility result"""
        try:
            comparison = await self.compare_documents(rfp_content, company_content)
            similarity_result = self._calculate_similarity(comparison["matches"])
            
            return {
                "eligible": similarity_result["eligible"],
                "scores": similarity_result["scores"],
                "metrics": similarity_result["metrics"],
                "matches": comparison["matches"]
            }
        except Exception as e:
            logger.error(f"Get result failed: {str(e)}")
            return {
                "eligible": False,
                "scores": {},
                "metrics": {},
                "matches": []
            }

if __name__ == "__main__":
    # Remove test code
    pass
