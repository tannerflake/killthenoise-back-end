#!/usr/bin/env python3
"""
AI Generation Test Script (Output to JSON)

This script tests AI issue generation and saves the results to a JSON file
for review and analysis.
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from pathlib import Path

import httpx

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"  # Test tenant
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
ISSUE_TYPES = ["bug", "feature_request", "support", "performance", "security", "integration"]
SEVERITY_LEVELS = [1, 2, 3, 4, 5]
STATUS_OPTIONS = ["open", "in-progress", "pending", "resolved", "closed"]


class AIGenerationOutputTester:
    """Test AI issue generation and save to JSON file."""

    def __init__(self, tenant_id: str, claude_api_key: str):
        self.tenant_id = tenant_id
        self.claude_api_key = claude_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def generate_realistic_issue(self, issue_type: str, source: str) -> Dict[str, Any]:
        """Generate a realistic issue using Claude AI."""
        
        prompt = f"""Generate a realistic {issue_type} issue for a SaaS application. 
        This should be a {source} ticket that a real customer might submit.

        Issue Type: {issue_type}
        Source: {source}

        Generate:
        1. A realistic title (max 100 characters)
        2. A detailed description (2-4 sentences)
        3. Appropriate severity (1-5, where 5 is critical)
        4. Realistic status
        5. Relevant tags (comma-separated)

        Make it sound like a real customer issue. Include specific details, error messages, 
        or user scenarios that would be typical for this type of issue.

        Respond in JSON format:
        {{
            "title": "Issue title",
            "description": "Detailed description...",
            "severity": 3,
            "status": "open",
            "tags": "tag1,tag2,tag3"
        }}"""

        try:
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["content"][0]["text"]
                
                # Parse JSON response
                try:
                    # Clean up the response
                    if content.startswith("```json"):
                        content = content[7:-3]
                    elif content.startswith("```"):
                        content = content[3:-3]
                    
                    issue_data = json.loads(content.strip())
                    
                    # Validate and set defaults
                    issue_data.setdefault("severity", random.randint(1, 5))
                    issue_data.setdefault("status", random.choice(STATUS_OPTIONS))
                    issue_data.setdefault("tags", "")
                    
                    return issue_data
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI response: {e}")
                    return self._generate_fallback_issue(issue_type, source)
            else:
                logger.warning(f"AI API error: {response.status_code}")
                return self._generate_fallback_issue(issue_type, source)
                
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._generate_fallback_issue(issue_type, source)

    def _generate_fallback_issue(self, issue_type: str, source: str) -> Dict[str, Any]:
        """Generate a fallback issue when AI fails."""
        
        fallback_issues = {
            "bug": {
                "title": f"Critical bug in {source} integration",
                "description": f"Users are experiencing intermittent failures when using the {source} integration. The issue appears to be related to authentication timeout handling.",
                "severity": 4,
                "status": "open",
                "tags": "bug,integration,authentication"
            },
            "feature_request": {
                "title": f"Request for enhanced {source} features",
                "description": f"Customers have requested additional features for the {source} integration, including better reporting and automation capabilities.",
                "severity": 3,
                "status": "pending",
                "tags": "feature-request,enhancement,reporting"
            },
            "support": {
                "title": f"General support question about {source}",
                "description": f"Customer has questions about configuring and optimizing their {source} integration for better performance.",
                "severity": 2,
                "status": "open",
                "tags": "support,configuration,help"
            },
            "performance": {
                "title": f"Performance issues with {source} sync",
                "description": f"The {source} synchronization is taking longer than expected, causing delays in data updates and user frustration.",
                "severity": 4,
                "status": "in-progress",
                "tags": "performance,sync,optimization"
            },
            "security": {
                "title": f"Security concern with {source} data handling",
                "description": f"Potential security vulnerability identified in how {source} data is processed and stored. Requires immediate attention.",
                "severity": 5,
                "status": "open",
                "tags": "security,vulnerability,urgent"
            },
            "integration": {
                "title": f"Integration issue between {source} and other systems",
                "description": f"Problems with the integration between {source} and other customer systems. Data is not syncing properly.",
                "severity": 3,
                "status": "in-progress",
                "tags": "integration,sync,data"
            }
        }
        
        return fallback_issues.get(issue_type, fallback_issues["support"])

    async def generate_issues(self, num_issues: int = 10) -> Dict[str, Any]:
        """Generate issues and save to JSON file."""
        
        if not self.claude_api_key:
            logger.error("❌ Claude API key not found. Set CLAUDE_API_KEY environment variable.")
            return {"success": False, "error": "Missing API key"}

        logger.info(f"🚀 Starting AI issue generation for {num_issues} issues...")
        
        results = {
            "metadata": {
                "tenant_id": self.tenant_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_issues": num_issues,
                "ai_model": "claude-3-haiku-20240307"
            },
            "issues": [],
            "statistics": {
                "hubspot_issues": 0,
                "jira_issues": 0,
                "by_type": {},
                "by_severity": {},
                "by_status": {}
            }
        }

        for i in range(num_issues):
            logger.info(f"📝 Generating issue {i+1}/{num_issues}...")
            
            # Generate issue data
            issue_type = random.choice(ISSUE_TYPES)
            source = random.choice(["hubspot", "jira"])
            
            issue_data = await self.generate_realistic_issue(issue_type, source)
            
            # Add metadata
            issue_record = {
                "id": i + 1,
                "type": issue_type,
                "source": source,
                "title": issue_data["title"],
                "description": issue_data["description"],
                "severity": issue_data["severity"],
                "status": issue_data["status"],
                "tags": issue_data["tags"],
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 72))).isoformat(),
                "ai_generated": True
            }
            
            # Add source-specific fields
            if source == "hubspot":
                issue_record["hubspot_ticket_id"] = f"HS-{random.randint(1000, 9999)}"
                results["statistics"]["hubspot_issues"] += 1
            elif source == "jira":
                issue_record["jira_issue_key"] = f"TEST-{random.randint(100, 999)}"
                results["statistics"]["jira_issues"] += 1
            
            results["issues"].append(issue_record)
            
            # Update statistics
            results["statistics"]["by_type"][issue_type] = results["statistics"]["by_type"].get(issue_type, 0) + 1
            results["statistics"]["by_severity"][str(issue_data["severity"])] = results["statistics"]["by_severity"].get(str(issue_data["severity"]), 0) + 1
            results["statistics"]["by_status"][issue_data["status"]] = results["statistics"]["by_status"].get(issue_data["status"], 0) + 1
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(1)
        
        # Save to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_generated_issues_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"✅ Generated {len(results['issues'])} issues")
        logger.info(f"📄 Results saved to: {filename}")
        
        return results

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()


async def main():
    """Main function to run the AI generation test."""
    
    if not CLAUDE_API_KEY:
        print("❌ Error: CLAUDE_API_KEY environment variable not set")
        print("Please set your Claude API key: export CLAUDE_API_KEY='your-key-here'")
        return
    
    print("🤖 AI Issue Generation Test (JSON Output)")
    print("=" * 60)
    
    # Get user input
    try:
        num_issues = int(input("Enter number of issues to generate (default 10): ") or "10")
        if num_issues < 1 or num_issues > 50:
            print("⚠️  Limiting to 50 issues maximum")
            num_issues = min(num_issues, 50)
    except ValueError:
        num_issues = 10
    
    print(f"🎯 Generating {num_issues} realistic test issues...")
    print("📝 This will save results to a JSON file")
    print("⏳ Please wait, this may take a few minutes...")
    print()
    
    # Create generator and run
    generator = AIGenerationOutputTester(TENANT_ID, CLAUDE_API_KEY)
    
    try:
        results = await generator.generate_issues(num_issues)
        
        if results.get("success") is False:
            print(f"❌ Generation failed: {results['error']}")
            return
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 GENERATION SUMMARY")
        print("=" * 60)
        print(f"✅ Total issues generated: {len(results['issues'])}")
        print(f"📊 HubSpot issues: {results['statistics']['hubspot_issues']}")
        print(f"📊 Jira issues: {results['statistics']['jira_issues']}")
        
        # Show type distribution
        print("\n📋 ISSUE TYPE DISTRIBUTION:")
        print("-" * 40)
        for issue_type, count in results['statistics']['by_type'].items():
            print(f"   {issue_type}: {count}")
        
        # Show severity distribution
        print("\n📊 SEVERITY DISTRIBUTION:")
        print("-" * 40)
        for severity, count in sorted(results['statistics']['by_severity'].items()):
            level_names = {1: "Minimal", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}
            level_name = level_names.get(int(severity), f"Level {severity}")
            print(f"   {level_name} ({severity}): {count}")
        
        # Show status distribution
        print("\n📈 STATUS DISTRIBUTION:")
        print("-" * 40)
        for status, count in results['statistics']['by_status'].items():
            print(f"   {status}: {count}")
        
        # Show sample issues
        print("\n📋 SAMPLE GENERATED ISSUES:")
        print("-" * 40)
        for i, issue in enumerate(results["issues"][:5], 1):
            print(f"{i}. [{issue['source'].upper()}] {issue['title']}")
            print(f"   Type: {issue['type']}, Severity: {issue['severity']}, Status: {issue['status']}")
            print(f"   Tags: {issue['tags']}")
            print()
        
        print("🎉 AI generation test complete!")
        print(f"📄 Full results saved to: ai_generated_issues_*.json")
        print("🔄 You can now review the generated issues and use them for testing")
        
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        logger.error(f"Generation failed: {e}")
    
    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
