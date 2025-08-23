#!/usr/bin/env python3
"""Test script for AI type classification functionality."""

import asyncio
import os
from uuid import uuid4

from app.services.ai_analysis_service import AIAnalysisService, create_ai_analysis_service


async def test_type_classification():
    """Test the AI type classification with sample tickets."""
    
    # Set up environment
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ CLAUDE_API_KEY environment variable not set")
        return
    
    tenant_id = uuid4()
    ai_service = create_ai_analysis_service(tenant_id, api_key)
    
    # Test cases
    test_cases = [
        {
            "title": "Add dark mode to the dashboard",
            "description": "Users have been requesting a dark mode option for the dashboard. This would improve user experience especially for users working in low-light environments.",
            "expected_type": "feature_request"
        },
        {
            "title": "Login button not working",
            "description": "When I click the login button, nothing happens. The page just stays on the login form without any error message.",
            "expected_type": "bug"
        },
        {
            "title": "Can you add export to PDF functionality?",
            "description": "It would be really helpful if we could export our reports to PDF format. Currently we can only export to CSV.",
            "expected_type": "feature_request"
        },
        {
            "title": "Error 500 when saving data",
            "description": "Getting a 500 server error whenever I try to save any data. This started happening after the last update.",
            "expected_type": "bug"
        }
    ]
    
    print("🧪 Testing AI Type Classification")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}:")
        print(f"Title: {test_case['title']}")
        print(f"Description: {test_case['description']}")
        print(f"Expected Type: {test_case['expected_type']}")
        
        try:
            # Test individual type analysis
            type_result = await ai_service.analyze_type(
                test_case['title'], 
                test_case['description']
            )
            
            print(f"🤖 AI Result: {type_result['type']}")
            print(f"📊 Confidence: {type_result['confidence']:.2f}")
            print(f"💭 Reasoning: {type_result['reasoning']}")
            
            # Check if prediction matches expected
            if type_result['type'] == test_case['expected_type']:
                print("✅ CORRECT")
            else:
                print("❌ INCORRECT")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Type classification test completed!")


if __name__ == "__main__":
    asyncio.run(test_type_classification())
