from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from anthropic import Anthropic

from app.db import get_db
from app.services.tenant_settings_service import TenantSettingsService


logger = logging.getLogger(__name__)


class AIAnalysisService:
    """Core AI service for analyzing tickets and issues using Claude API."""

    def __init__(self, tenant_id: UUID, api_key: str, session=None):
        self.tenant_id = tenant_id
        self.client = Anthropic(api_key=api_key)
        self.session = session

    async def analyze_ticket_comprehensive(
        self, title: str, description: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive AI analysis of a ticket."""
        try:
            # Get tenant-specific instructions
            tenant_instructions = await self._get_tenant_instructions()
            
            # Run analyses in parallel for better performance
            analyses = await asyncio.gather(
                self.analyze_severity(title, description, context, tenant_instructions),
                self.analyze_sentiment(title, description),
                self.analyze_categorization(title, description),
                self.analyze_type(title, description, tenant_instructions),
                return_exceptions=True
            )

            severity_result = analyses[0] if not isinstance(analyses[0], Exception) else {}
            sentiment_result = analyses[1] if not isinstance(analyses[1], Exception) else {}
            category_result = analyses[2] if not isinstance(analyses[2], Exception) else {}
            type_result = analyses[3] if not isinstance(analyses[3], Exception) else {}

            return {
                "severity": severity_result,
                "sentiment": sentiment_result,
                "categorization": category_result,
                "type": type_result,
                "tenant_id": str(self.tenant_id)
            }

        except Exception as e:
            logger.error(f"Comprehensive analysis failed for tenant {self.tenant_id}: {e}")
            return self._get_fallback_analysis()

    async def _get_tenant_instructions(self) -> Dict[str, str]:
        """Get tenant-specific instructions for AI analysis."""
        if not self.session:
            return {}
        
        try:
            settings_service = TenantSettingsService(self.session)
            return {
                "severity_instructions": await settings_service.get_severity_calculation_instructions(self.tenant_id) or "",
                "type_instructions": await settings_service.get_type_classification_instructions(self.tenant_id) or "",
                "grouping_instructions": await settings_service.get_grouping_instructions(self.tenant_id) or ""
            }
        except Exception as e:
            logger.warning(f"Failed to get tenant instructions: {e}")
            return {}

    async def analyze_severity(
        self, title: str, description: str, context: Dict[str, Any], tenant_instructions: Dict[str, str]
    ) -> Dict[str, Any]:
        """Analyze ticket severity using AI with tenant-specific instructions."""
        try:
            prompt = self._build_severity_prompt(title, description, context, tenant_instructions)
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_severity_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Severity analysis failed for tenant {self.tenant_id}: {e}")
            return {"severity_score": 50, "confidence": 0.0, "reasoning": "Fallback"}

    async def analyze_sentiment(self, title: str, description: str) -> Dict[str, Any]:
        """Analyze customer sentiment and urgency."""
        try:
            prompt = self._build_sentiment_prompt(title, description)
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_sentiment_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Sentiment analysis failed for tenant {self.tenant_id}: {e}")
            return {"sentiment": "neutral", "urgency": 0.5, "confidence": 0.0}

    async def analyze_categorization(
        self, title: str, description: str
    ) -> Dict[str, Any]:
        """Analyze and categorize the ticket."""
        try:
            prompt = self._build_categorization_prompt(title, description)
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_categorization_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Categorization failed for tenant {self.tenant_id}: {e}")
            return {"category": "general", "tags": [], "confidence": 0.0}

    async def analyze_type(self, title: str, description: str, tenant_instructions: Dict[str, str]) -> Dict[str, Any]:
        """Analyze whether the issue is a feature request or bug with tenant-specific instructions."""
        try:
            prompt = self._build_type_prompt(title, description, tenant_instructions)
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_type_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Type analysis failed for tenant {self.tenant_id}: {e}")
            return {"type": "bug", "confidence": 0.0, "reasoning": "Fallback"}

    def _build_severity_prompt(
        self, title: str, description: str, context: Dict[str, Any], tenant_instructions: Dict[str, str]
    ) -> str:
        """Build prompt for severity analysis with tenant-specific instructions."""
        tenant_severity_instructions = tenant_instructions.get("severity_instructions", "")
        
        base_prompt = f"""Analyze this customer support ticket and determine its severity level.

Title: {title}
Description: {description or 'No description provided'}
Priority: {context.get('priority', 'Not specified')}
Customer Type: {context.get('customer_type', 'Unknown')}

Rate severity from 0-100 where:
0-20 = Minimal (info request, minor question)
21-40 = Low (non-urgent issue, workaround available)
41-60 = Medium (affects functionality, no workaround)
61-80 = High (significant business impact, urgent)
81-100 = Critical (system down, revenue impact, security issue)

Respond with JSON format:
{{"severity_score": <0-100>, "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}"""

        if tenant_severity_instructions:
            base_prompt += f"""

TENANT-SPECIFIC INSTRUCTIONS:
{tenant_severity_instructions}

Please follow these tenant-specific instructions when calculating severity scores."""

        return base_prompt

    def _build_sentiment_prompt(self, title: str, description: str) -> str:
        """Build prompt for sentiment analysis."""
        return f"""Analyze the customer sentiment and urgency in this support ticket.

Title: {title}
Description: {description or 'No description provided'}

Determine:
1. Sentiment: frustrated, neutral, or satisfied
2. Urgency: 0.0 (not urgent) to 1.0 (extremely urgent)

Respond with JSON format:
{{"sentiment": "<frustrated|neutral|satisfied>", "urgency": <0.0-1.0>, "confidence": <0.0-1.0>}}"""

    def _build_categorization_prompt(self, title: str, description: str) -> str:
        """Build prompt for categorization analysis."""
        return f"""Categorize this support ticket and suggest relevant tags.

Title: {title}
Description: {description or 'No description provided'}

Categories: technical, billing, account, feature_request, bug_report, integration, security, general

Respond with JSON format:
{{"category": "<category>", "tags": ["<tag1>", "<tag2>"], "confidence": <0.0-1.0>}}"""

    def _build_type_prompt(self, title: str, description: str, tenant_instructions: Dict[str, str]) -> str:
        """Build prompt for type analysis with tenant-specific instructions."""
        tenant_type_instructions = tenant_instructions.get("type_instructions", "")
        
        base_prompt = f"""Analyze this support ticket and determine if it's a feature request or a bug.

Title: {title}
Description: {description or 'No description provided'}

Classify as:
- "feature_request": User wants new functionality, enhancement, or capability
- "bug": Something is broken, not working as expected, or malfunctioning

Consider these indicators:
Feature Request: "can you add", "would be nice to have", "wish there was", "suggestion", "enhancement"
Bug: "not working", "broken", "error", "issue", "problem", "doesn't work", "fails"

Respond with JSON format:
{{"type": "<feature_request|bug>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}"""

        if tenant_type_instructions:
            base_prompt += f"""

TENANT-SPECIFIC INSTRUCTIONS:
{tenant_type_instructions}

Please follow these tenant-specific instructions when classifying the issue type."""

        return base_prompt

    def _parse_severity_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response for severity analysis."""
        try:
            # Clean the response and extract JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            result = json.loads(response_text)
            
            # Validate the response - now using 0-100 scale
            severity = max(0, min(100, int(result.get("severity_score", 50))))
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            return {
                "severity_score": severity,
                "confidence": confidence,
                "reasoning": result.get("reasoning", "AI analysis")
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse severity response: {e}")
            return {"severity_score": 50, "confidence": 0.0, "reasoning": "Parse error"}

    def _parse_sentiment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response for sentiment analysis."""
        try:
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            result = json.loads(response_text)
            
            sentiment = result.get("sentiment", "neutral")
            if sentiment not in ["frustrated", "neutral", "satisfied"]:
                sentiment = "neutral"
            
            urgency = max(0.0, min(1.0, float(result.get("urgency", 0.5))))
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            return {
                "sentiment": sentiment,
                "urgency": urgency,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse sentiment response: {e}")
            return {"sentiment": "neutral", "urgency": 0.5, "confidence": 0.0}

    def _parse_categorization_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response for categorization."""
        try:
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            result = json.loads(response_text)
            
            valid_categories = [
                "technical", "billing", "account", "feature_request", 
                "bug_report", "integration", "security", "general"
            ]
            
            category = result.get("category", "general")
            if category not in valid_categories:
                category = "general"
            
            tags = result.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            return {
                "category": category,
                "tags": tags[:5],  # Limit to 5 tags
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse categorization response: {e}")
            return {"category": "general", "tags": [], "confidence": 0.0}

    def _parse_type_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response for type analysis."""
        try:
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            result = json.loads(response_text)
            
            issue_type = result.get("type", "bug")
            if issue_type not in ["feature_request", "bug"]:
                issue_type = "bug"  # Default to bug if invalid type
            
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            return {
                "type": issue_type,
                "confidence": confidence,
                "reasoning": result.get("reasoning", "AI analysis")
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse type response: {e}")
            return {"type": "bug", "confidence": 0.0, "reasoning": "Parse error"}

    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails."""
        return {
            "severity": {"severity_score": 50, "confidence": 0.0, "reasoning": "Fallback"},
            "sentiment": {"sentiment": "neutral", "urgency": 0.5, "confidence": 0.0},
            "categorization": {"category": "general", "tags": [], "confidence": 0.0},
            "type": {"type": "bug", "confidence": 0.0, "reasoning": "Fallback"},
            "tenant_id": str(self.tenant_id)
        }


def create_ai_analysis_service(tenant_id: UUID, api_key: str, session=None) -> AIAnalysisService:
    """Factory function for creating tenant-specific AI analysis services."""
    return AIAnalysisService(tenant_id, api_key, session)