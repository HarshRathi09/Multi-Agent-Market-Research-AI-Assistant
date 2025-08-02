from langchain_core.tools import BaseTool
from state import ResearchState
from Tools.webSearchTool import WebSearchTool
import logging
import asyncio
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ResourceCollectorTool(BaseTool):
    name: str = "resource_collector"
    description: str = "Collect relevant resources and datasets"
    
    def __init__(self, web_search_tool: WebSearchTool):
        super().__init__()
        self._web_search_tool = web_search_tool
    
    async def _search_resources_async(self, queries: List[str], max_results: int = 3) -> List[Dict[str, Any]]:
        """Run multiple resource searches in parallel"""
        all_results = []
        
        async def search_one(query: str):
            try:
                results = self._web_search_tool._run(query=query, max_results=max_results)
                return results
            except Exception as e:
                logger.error(f"Error in async resource search for query '{query}': {str(e)}")
                return []
        
        # Create tasks for all queries
        tasks = [search_one(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        for res in results:
            all_results.extend(res)
            
        return all_results
    
    def _run(self, state: ResearchState) -> ResearchState:
        logger.debug(f"Collecting resources for {state['company_name']}")
        
        # Initialize empty resource list if needed
        if 'resource_links' not in state:
            state['resource_links'] = []
        
        # Generate search queries based on company, industry, and use cases
        queries = []
        
        # Add general industry resources
        queries.append(f"AI ML datasets resources {state['industry']} industry")
        queries.append(f"GitHub repositories {state['industry']} machine learning")
        queries.append(f"Kaggle datasets {state['industry']} analysis")
        
        # Add use case specific queries (limit to first 3 use cases to avoid too many API calls)
        for use_case in state.get('use_cases', [])[:3]:
            objective = use_case.get('objective', '')
            if objective:
                queries.append(f"Datasets and resources for {objective} in {state['industry']}")
        
        # Add offering specific queries
        for offering in state.get('key_offerings', [])[:2]:
            queries.append(f"AI ML datasets for {offering} in {state['industry']}")
        
        try:
            # Run searches in parallel
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resource_searches = loop.run_until_complete(self._search_resources_async(queries))
            loop.close()
            
            # Filter for relevant resources with scoring
            resource_scores = {}
            
            # Define relevant domains and their importance scores
            relevant_domains = {
                'kaggle.com': 10,
                'github.com': 9,
                'huggingface.co': 8,
                'paperswithcode.com': 7,
                'tensorflow.org': 6,
                'pytorch.org': 6,
                'scikit-learn.org': 5,
                'openml.org': 5,
                'data.gov': 4,
                'google.com/dataset': 4
            }
            
            # Score each search result
            for result in resource_searches:
                url = result.get('url', '')
                if not url:
                    continue
                
                # Skip if already processed
                if url in resource_scores:
                    continue
                
                # Calculate relevance score
                base_score = result.get('relevance_score', 0.5) * 5  # Convert to 0-5 scale
                domain_score = 0
                
                # Check if URL contains any relevant domain
                for domain, importance in relevant_domains.items():
                    if domain in url.lower():
                        domain_score = importance
                        break
                
                # Skip URLs with no domain match
                if domain_score == 0:
                    continue
                
                # Calculate final score
                final_score = base_score * domain_score
                resource_scores[url] = final_score
            
            # Sort URLs by score and take top 15
            sorted_urls = sorted(resource_scores.keys(), key=lambda url: resource_scores[url], reverse=True)[:15]
            
            # Add new unique URLs to the resource_links
            existing_urls = set(state.get('resource_links', []))
            for url in sorted_urls:
                if url not in existing_urls:
                    state['resource_links'].append(url)
            
            logger.debug(f"Collected {len(state['resource_links'])} resource links")
            
        except Exception as e:
            logger.error(f"Error collecting resources: {str(e)}")
            state['errors'].append(f"Resource collection error: {str(e)}")
        
        return state
    
    def _is_dataset_url(self, url: str) -> bool:
        """Check if URL is likely to contain a dataset"""
        dataset_indicators = [
            'dataset', 'data', 'kaggle', 'github', 'huggingface', 
            '.csv', '.json', '.parquet', '.xlsx', 'opendata'
        ]
        return any(indicator in url.lower() for indicator in dataset_indicators)