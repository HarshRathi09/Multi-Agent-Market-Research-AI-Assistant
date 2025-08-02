# Tools/costBenefitTool.py
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from state import ResearchState
from typing import Dict, Any, List

class CostBenefitTool(BaseTool):
    name: str = "cost_benefit_analysis"
    description: str = "Analyze costs and benefits of AI implementation"
    
    def __init__(self, llm: ChatGroq):
        super().__init__()
        self._llm = llm
    
    def _estimate_costs_benefits(self, use_case: Dict[str, Any], industry: str, implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs and benefits for a specific use case"""
        
        # Prepare context for cost-benefit analysis
        use_case_context = f"""
        Use Case: {use_case.get('case', '')}
        Objective: {use_case.get('objective', '')}
        AI Application: {use_case.get('ai_application', '')}
        Cross-Functional Benefits: {', '.join(use_case.get('cross_functional_benefit', []))}
        
        """
        
        # Generate cost-benefit analysis using LLM
        analysis_prompt = f"""
        Provide a detailed cost-benefit analysis for implementing the following AI use case in the {industry} industry:
        
        {use_case_context}
        
        Create a comprehensive analysis in JSON format, withhout any explanations or additional text and without JSON backticks:
        {{
            "implementation_costs": {{
                "technology": {{
                    "hardware": "Estimated cost range",
                    "software": "Estimated cost range",
                    "infrastructure": "Estimated cost range",
                    "total_tech_costs": "Estimated total technology costs"
                }},
                "human_resources": {{
                    "internal_team": "Estimated cost range",
                    "contractors": "Estimated cost range",
                    "training": "Estimated cost range",
                    "total_hr_costs": "Estimated total HR costs"
                }},
                "other_costs": ["Other cost 1", "Other cost 2"],
                "total_cost_range": "Estimated total cost range"
            }},
            "expected_benefits": {{
                "quantitative": [
                    {{
                        "benefit": "Benefit description",
                        "estimated_value": "Estimated value range",
                        "timeframe": "Expected timeframe"
                    }}
                ],
                "qualitative": ["Qualitative benefit 1", "Qualitative benefit 2"]
            }},
            "roi_analysis": {{
                "payback_period": "Estimated payback period",
                "first_year_roi": "Estimated first year ROI percentage",
                "three_year_roi": "Estimated three year ROI percentage",
                "non_financial_benefits": ["Benefit 1", "Benefit 2"]
            }},
            "risk_factors": ["Risk 1", "Risk 2"]
        }}
        
        Use realistic industry-standard cost ranges and ROI estimations based on similar AI implementations.
        """
        
        response = self._llm.invoke([HumanMessage(content=analysis_prompt)])
        
        try:
            # Extract JSON from response
            content = response.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                analysis_json = content[start_idx:end_idx]
                analysis = eval(analysis_json)  # Using eval instead of json.loads for flexibility
                return analysis
            return {}
        except Exception as e:
            print(f"Error parsing cost-benefit analysis: {e}")
            return {}
    
    def _run(self, state: ResearchState) -> ResearchState:
        # Generate cost-benefit analysis for each use case with an implementation plan
        cost_benefit_analyses = []
        
        for i, use_case in enumerate(state['use_cases']):
            if i < len(state.get('implementation_plans', [])):
                implementation_plan = state['implementation_plans'][i]['plan']
                analysis = self._estimate_costs_benefits(use_case, state['industry'], implementation_plan)
                cost_benefit_analyses.append({
                    "use_case": use_case.get('case', ''),
                    "analysis": analysis
                })
        print(f"Cost-benefit analyses: {cost_benefit_analyses}")
        state['cost_benefit_analyses'] = cost_benefit_analyses
        
        return state