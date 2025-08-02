from typing import Any, Dict, List, TypedDict
from pydantic import BaseModel, Field

class UseCase(BaseModel):
    case: str
    objective: str
    ai_application: str
    cross_functional_benefit: List[str]
    articles: List[str]

class ResearchState(TypedDict):
    company_name: str
    industry: str
    key_offerings: List[str]
    market_trends: List[str]
    industry_insights: str
    web_search_results: List[Dict[str, Any]]
    use_cases: List[Dict[str, Any]]
    resource_links: List[str]
    swot_analysis: Dict[str, List[str]]
    ai_recommendations: List[str]
    errors: List[str]
    competitor_analysis_tool: str
    implementation_plans: str
    cost_benefit_analyses: str
    competitors: List[Dict[str, Any]]
    
