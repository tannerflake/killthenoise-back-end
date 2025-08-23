from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from app.services.ai_analysis_service import AIAnalysisService, create_ai_analysis_service
from app.services.ai_config_service import get_claude_api_key, is_ai_enabled


logger = logging.getLogger(__name__)


class AIIntegrationService:
    """Integration service that manages AI analysis for ticket processing."""

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self._ai_service: Optional[AIAnalysisService] = None

    async def enhance_ticket_data(
        self, ticket_data: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance ticket data with AI analysis."""
        if not is_ai_enabled():
            logger.info(f"AI disabled for tenant {self.tenant_id}, using fallback")
            return self._apply_fallback_analysis(ticket_data)

        try:
            ai_service = self._get_ai_service()
            if not ai_service:
                return self._apply_fallback_analysis(ticket_data)

            # Extract ticket information
            title = ticket_data.get("title", "")
            description = ticket_data.get("description", "")

            # Perform AI analysis
            analysis = await ai_service.analyze_ticket_comprehensive(
                title, description, context
            )

            # Apply AI analysis to ticket data
            enhanced_data = ticket_data.copy()
            enhanced_data.update(self._apply_ai_analysis(analysis, ticket_data))

            logger.info(f"AI analysis completed for tenant {self.tenant_id}")
            return enhanced_data

        except Exception as e:
            logger.error(f"AI analysis failed for tenant {self.tenant_id}: {e}")
            return self._apply_fallback_analysis(ticket_data)

    def _get_ai_service(self) -> Optional[AIAnalysisService]:
        """Get or create AI analysis service instance."""
        if self._ai_service is None:
            api_key = get_claude_api_key()
            if not api_key:
                logger.warning(f"No Claude API key available for tenant {self.tenant_id}")
                return None
            
            self._ai_service = create_ai_analysis_service(self.tenant_id, api_key)
        
        return self._ai_service

    def _apply_ai_analysis(
        self, analysis: Dict[str, Any], original_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply AI analysis results to ticket data."""
        updates = {}

        # Mark as AI-enabled
        updates["ai_enabled"] = True

        # Apply severity analysis
        severity_data = analysis.get("severity", {})
        if severity_data.get("confidence", 0) > 0.3:  # Only use if confident
            updates["severity"] = severity_data.get("severity_score")
            updates["ai_severity_confidence"] = severity_data.get("confidence")
            updates["ai_severity_reasoning"] = severity_data.get("reasoning")

        # Apply sentiment analysis
        sentiment_data = analysis.get("sentiment", {})
        if sentiment_data.get("confidence", 0) > 0.3:
            updates["ai_sentiment"] = sentiment_data.get("sentiment")
            updates["ai_urgency"] = sentiment_data.get("urgency")
            updates["ai_sentiment_confidence"] = sentiment_data.get("confidence")

        # Apply categorization
        category_data = analysis.get("categorization", {})
        if category_data.get("confidence", 0) > 0.3:
            updates["ai_category"] = category_data.get("category")
            updates["ai_tags"] = ",".join(category_data.get("tags", []))
            updates["ai_category_confidence"] = category_data.get("confidence")

        # Apply type analysis
        type_data = analysis.get("type", {})
        if type_data.get("confidence", 0) > 0.3:
            updates["type"] = type_data.get("type")
            updates["ai_type_confidence"] = type_data.get("confidence")
            updates["ai_type_reasoning"] = type_data.get("reasoning")

        # Preserve original data if AI confidence is low
        if not updates.get("severity"):
            updates["severity"] = original_data.get("severity", 3)
        
        if not updates.get("type"):
            updates["type"] = original_data.get("type", "bug")

        # Ensure all AI fields have default values
        updates.setdefault("ai_severity_confidence", 0.0)
        updates.setdefault("ai_sentiment_confidence", 0.0)
        updates.setdefault("ai_category_confidence", 0.0)
        updates.setdefault("ai_type_confidence", 0.0)
        updates.setdefault("ai_urgency", 0.5)

        # Remove None values to avoid database issues
        updates = {k: v for k, v in updates.items() if v is not None}

        return updates

    def _apply_fallback_analysis(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fallback analysis when AI is unavailable."""
        enhanced_data = ticket_data.copy()
        
        # Use existing severity if available, otherwise default to medium
        if not enhanced_data.get("severity"):
            enhanced_data["severity"] = 3
        
        # Add fallback indicators with proper default values
        enhanced_data["ai_enabled"] = False
        enhanced_data["ai_severity_confidence"] = 0.0
        enhanced_data["ai_sentiment_confidence"] = 0.0
        enhanced_data["ai_category_confidence"] = 0.0
        enhanced_data["ai_urgency"] = 0.5  # Default neutral urgency
        
        # Remove None values to avoid database issues
        enhanced_data = {k: v for k, v in enhanced_data.items() if v is not None}
        
        return enhanced_data

    async def analyze_frequency(
        self, ticket_data: Dict[str, Any], historical_tickets: list
    ) -> int:
        """Analyze frequency of similar issues (placeholder for future implementation)."""
        # TODO: Implement AI-powered frequency analysis
        # This would compare current ticket against historical tickets
        # to find similar issues and calculate frequency
        return 1  # Default frequency for now

    async def close(self):
        """Clean up resources."""
        if self._ai_service and hasattr(self._ai_service, 'client'):
            # Claude client doesn't need explicit cleanup, but we clear the reference
            self._ai_service = None


def create_ai_integration_service(tenant_id: UUID) -> AIIntegrationService:
    """Factory function for creating tenant-specific AI integration services."""
    return AIIntegrationService(tenant_id)