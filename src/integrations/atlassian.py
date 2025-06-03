"""Atlassian integration base connector"""

import asyncio
from typing import Any, Dict, List, Optional

from atlassian import Confluence, Jira
from loguru import logger

from ..config import settings


class AtlassianConnector:
    """Base connector for Atlassian products"""
    
    def __init__(self):
        self.base_url = settings.atlassian_base_url
        self.email = settings.atlassian_email
        self.api_token = settings.atlassian_api_token
        
        # Initialize clients
        self.confluence = None
        self.jira = None
        
        if self.base_url and self.email and self.api_token:
            self._initialize_clients()
        else:
            logger.warning("Atlassian credentials not configured")
            
    def _initialize_clients(self):
        """Initialize Atlassian API clients"""
        try:
            self.confluence = Confluence(
                url=self.base_url,
                username=self.email,
                password=self.api_token,
                cloud=True
            )
            
            self.jira = Jira(
                url=self.base_url,
                username=self.email,
                password=self.api_token,
                cloud=True
            )
            
            logger.info("Atlassian clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Atlassian clients: {e}")
            
    async def test_connection(self) -> Dict[str, bool]:
        """Test connections to Atlassian services"""
        results = {
            "confluence": False,
            "jira": False
        }
        
        # Test Confluence
        if self.confluence:
            try:
                self.confluence.get_all_spaces(limit=1)
                results["confluence"] = True
            except Exception as e:
                logger.error(f"Confluence connection test failed: {e}")
                
        # Test Jira
        if self.jira:
            try:
                self.jira.projects()
                results["jira"] = True
            except Exception as e:
                logger.error(f"Jira connection test failed: {e}")
                
        return results
        
    async def setup_webhooks(self, webhook_url: str) -> Dict[str, Any]:
        """Set up webhooks for real-time updates"""
        results = {
            "confluence": [],
            "jira": []
        }
        
        # Confluence webhooks
        if self.confluence:
            confluence_events = [
                "page_created",
                "page_updated",
                "page_removed",
                "page_restored",
                "comment_created",
                "comment_updated"
            ]
            
            # Note: Confluence Cloud doesn't support webhooks via API
            # Would need to use Confluence Connect app
            logger.info("Confluence webhooks require Connect app")
            
        # Jira webhooks
        if self.jira:
            try:
                # Create Jira webhook
                webhook_data = {
                    "name": "RAG System Webhook",
                    "url": webhook_url,
                    "events": [
                        "jira:issue_created",
                        "jira:issue_updated",
                        "jira:issue_deleted",
                        "comment_created",
                        "comment_updated"
                    ],
                    "filters": {
                        "issue-related-events-section": {}
                    },
                    "excludeBody": False
                }
                
                # Create webhook via REST API
                response = self.jira._session.post(
                    f"{self.base_url}/rest/webhooks/1.0/webhook",
                    json=webhook_data
                )
                
                if response.status_code == 201:
                    webhook_id = response.json()["id"]
                    results["jira"].append(webhook_id)
                    logger.info(f"Created Jira webhook: {webhook_id}")
                else:
                    logger.error(f"Failed to create Jira webhook: {response.text}")
                    
            except Exception as e:
                logger.error(f"Failed to setup Jira webhooks: {e}")
                
        return results
        
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content from Confluence"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
        
    async def search_content(
        self,
        query: str,
        limit: int = 10,
        service: str = "both"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search across Atlassian services"""
        results = {
            "confluence": [],
            "jira": []
        }
        
        tasks = []
        
        # Search Confluence
        if service in ["confluence", "both"] and self.confluence:
            tasks.append(self._search_confluence(query, limit))
            
        # Search Jira
        if service in ["jira", "both"] and self.jira:
            tasks.append(self._search_jira(query, limit))
            
        # Execute searches in parallel
        if tasks:
            search_results = await asyncio.gather(*tasks)
            
            if service in ["confluence", "both"] and self.confluence:
                results["confluence"] = search_results[0]
                
            if service in ["jira", "both"] and self.jira:
                idx = 1 if service == "both" else 0
                results["jira"] = search_results[idx]
                
        return results
        
    async def _search_confluence(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Confluence content"""
        try:
            cql = f'text ~ "{query}"'
            search_results = self.confluence.cql(
                cql,
                limit=limit,
                expand="body.storage,metadata"
            )
            
            results = []
            for result in search_results.get("results", []):
                results.append({
                    "id": result["content"]["id"],
                    "title": result["content"]["title"],
                    "type": result["content"]["type"],
                    "url": f"{self.base_url}/wiki{result['content']['_links']['webui']}",
                    "excerpt": result.get("excerpt", ""),
                    "last_modified": result["content"]["version"]["when"]
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Confluence search failed: {e}")
            return []
            
    async def _search_jira(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Jira issues"""
        try:
            jql = f'text ~ "{query}"'
            issues = self.jira.jql(
                jql,
                limit=limit,
                fields="summary,description,issuetype,status,priority,created,updated"
            )
            
            results = []
            for issue in issues.get("issues", []):
                results.append({
                    "id": issue["id"],
                    "key": issue["key"],
                    "summary": issue["fields"]["summary"],
                    "type": issue["fields"]["issuetype"]["name"],
                    "status": issue["fields"]["status"]["name"],
                    "priority": issue["fields"]["priority"]["name"],
                    "url": f"{self.base_url}/browse/{issue['key']}",
                    "created": issue["fields"]["created"],
                    "updated": issue["fields"]["updated"]
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Jira search failed: {e}")
            return []