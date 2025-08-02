from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from tavily import TavilyClient
import time
import hashlib
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    query: str = Field(description="Search query string")
    max_results: int = Field(default=5, description="Maximum number of search results to return")
    cache_ttl: int = Field(default=3600, description="Time to live for cached results in seconds")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Perform web search using Tavily API with caching"
    args_schema: type[BaseModel] = WebSearchInput
    
    def __init__(self, tavily_api_key: str, cache_size: int = 100):
        super().__init__()
        self._tavily_client = TavilyClient(api_key=tavily_api_key)
        self._cache = {}
        self._cache_timestamps = {}
        self._max_cache_size = cache_size
        logger.debug(f"Initialized WebSearchTool with cache_size={cache_size}")
    
    def _get_cache_key(self, query: str, max_results: int) -> str:
        """Generate a cache key for the search query"""
        return hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str, cache_ttl: int) -> Optional[List[Dict[str, Any]]]:
        """Get results from cache if available and not expired"""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp <= cache_ttl:
                logger.debug(f"Cache hit for key: {cache_key}")
                return self._cache[cache_key]
            else:
                logger.debug(f"Cache expired for key: {cache_key}")
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        return None
    
    def _add_to_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Add results to cache with timestamp"""
        # If cache is full, remove oldest entry
        if len(self._cache) >= self._max_cache_size:
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        self._cache[cache_key] = results
        self._cache_timestamps[cache_key] = time.time()
        logger.debug(f"Added to cache: {cache_key}")
    
    def _run(self, query: str, max_results: int = 5, cache_ttl: int = 3600) -> List[Dict[str, Any]]:
        """Perform web search with caching and proper error handling"""
        logger.debug(f"Running web search: query='{query}', max_results={max_results}")
        
        # Clean and normalize query to improve cache hits
        query = query.strip().lower()
        
        # Check cache
        cache_key = self._get_cache_key(query, max_results)
        cached_results = self._get_from_cache(cache_key, cache_ttl)
        if cached_results:
            return cached_results
        
        # Perform search with retries
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                search_results = self._tavily_client.search(
                    query=query,
                    max_results=max_results,
                    include_answer=True,
                    include_raw_content=True
                )
                
                # Process results
                results = []
                for result in search_results.get('results', []):
                    if isinstance(result, dict):
                        results.append({
                            'title': result.get('title', 'No Title'),
                            'url': result.get('url', ''),
                            'content': result.get('raw_content', '')[:1000] + '...' if result.get('raw_content') else '',
                            'relevance_score': float(result.get('score', 0))
                        })
                
                # Save to cache if we got results
                if results:
                    self._add_to_cache(cache_key, results)
                    return results
                return [{"title": "No results found", "url": "", "content": "", "relevance_score": 0}]
                
            except Exception as e:
                logger.error(f"Web search error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    return [{"title": "Search Error", "url": "", "content": f"Web search failed after {max_retries} attempts: {str(e)}", "relevance_score": 0}]