# Tools/competitorAnalysisTool.py
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from state import ResearchState
from Tools.webSearchTool import WebSearchTool

class CompetitorAnalysisTool(BaseTool):
    name: str = "competitor_analysis"
    description: str = "Analyze competitors in the industry"
    
    def __init__(self, llm: ChatGroq, web_search_tool: WebSearchTool):
        super().__init__()
        self._llm = llm
        self._web_search_tool = web_search_tool
    
    def _identify_competitors(self, company_name: str, industry: str) -> List[Dict[str, Any]]:
        """Identify top competitors using web search"""
        # Search for competitors
        competitor_search = self._web_search_tool._run(
            query=f"top competitors of {company_name} in {industry} industry",
            max_results=5
        )
        
        # Extract context for LLM
        competitor_context = "\n\n".join([
            f"Title: {result['title']}\nContent: {result['content']}"
            for result in competitor_search
        ])
        
        # Generate competitor list using LLM
        competitors_prompt = f"""
        Based on the following information about {company_name} in the {industry} industry,
        identify their top 3-5 direct competitors.
        
        Information:
        {competitor_context}
        
        For each competitor, provide:
        1. Company name
        2. Brief description (1-2 sentences)
        3. Key AI/ML initiatives they're known for (if any)
        
        Format as JSON, without any explanations or additional text and without JSON backticks:
        [
            {{
                "name": "Competitor Name",
                "description": "Brief description",
                "ai_initiatives": ["Initiative 1", "Initiative 2"]
            }}
        ]
        
        Focus on direct competitors with similar offerings or target markets.
        """
        
        response = self._llm.invoke([HumanMessage(content=competitors_prompt)])
        
        try:
            # Extract JSON from response
            content = response.content
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                competitors_json = content[start_idx:end_idx]
                competitors = eval(competitors_json)  # Using eval instead of json.loads for flexibility
                return competitors
            return []
        except Exception as e:
            print(f"Error parsing competitors: {e}")
            return []
    
    def _analyze_competitive_positioning(self, company_name: str, industry: str, competitors: List[Dict[str, Any]], key_offerings: List[str]) -> Dict[str, Any]:
        """Analyze competitive positioning against identified competitors"""
        
        # Create context for competitive analysis
        offerings_str = ", ".join(key_offerings)
        competitors_str = "\n".join([
            f"- {comp['name']}: {comp['description']}\n  AI Initiatives: {', '.join(comp['ai_initiatives'])}"
            for comp in competitors
        ])
        
        # Additional search for competitive positioning
        positioning_search = self._web_search_tool._run(
            query=f"{company_name} competitive advantage AI ML {industry} compared to competitors",
            max_results=3
        )
        
        positioning_context = "\n\n".join([
            f"Title: {result['title']}\nContent: {result['content']}"
            for result in positioning_search
        ])
        
        # Generate competitive analysis using LLM
        positioning_prompt = f"""
        Analyze the competitive positioning of {company_name} in the {industry} industry compared to these competitors:
        
        {competitors_str}
        
        {company_name}'s key offerings: {offerings_str}
        
        Additional context:
        {positioning_context}
        
        Provide a comprehensive competitive analysis in JSON format, without JSON backticks:
        {{
            "strengths": ["Strength 1", "Strength 2"],
            "weaknesses": ["Weakness 1", "Weakness 2"],
            "opportunities": ["Opportunity 1", "Opportunity 2"],
            "threats": ["Threat 1", "Threat 2"],
            "ai_maturity_score": 0-10,
            "ai_maturity_explanation": "Brief explanation of the AI maturity score",
            "competitive_positioning": "Summary of competitive positioning (3-4 sentences)"
        }}
        """
        
        response = self._llm.invoke([HumanMessage(content=positioning_prompt)])
        
        try:
            # Extract JSON from response
            content = response.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                positioning_json = content[start_idx:end_idx]
                positioning = eval(positioning_json)  # Using eval instead of json.loads for flexibility
                return positioning
            return {}
        except Exception as e:
            print(f"Error parsing competitive positioning: {e}")
            return {}
    
    def _run(self, state: ResearchState) -> ResearchState:
        # First, identify competitors
        competitors = self._identify_competitors(state['company_name'], state['industry'])
        state['competitors'] = competitors
        
        # Then analyze competitive positioning
        positioning = self._analyze_competitive_positioning(
            state['company_name'], 
            state['industry'],
            competitors,
            state['key_offerings']
        )
        
        state['competitor_analysis_tool'] = positioning
        
        return state