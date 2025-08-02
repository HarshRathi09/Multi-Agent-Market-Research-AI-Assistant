from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from state import ResearchState
from typing import Dict, Any, List

class ImplementationPlanningTool(BaseTool):
    name: str = "implementation_planning"
    description: str = "Generate implementation roadmaps for AI use cases"
    
    def __init__(self, llm: ChatGroq):
        super().__init__()
        self._llm = llm
    
    def _create_implementation_plan(self, use_case: Dict[str, Any], industry: str) -> Dict[str, Any]:
        """Create detailed implementation plan for a specific use case"""
        
        # Prepare context for implementation planning
        use_case_context = f"""
        Use Case: {use_case.get('case', '')}
        Objective: {use_case.get('objective', '')}
        AI Application: {use_case.get('ai_application', '')}
        Cross-Functional Benefits: {', '.join(use_case.get('cross_functional_benefit', []))}
        """
        
        # Generate implementation plan using LLM
        planning_prompt = f"""
        Create a detailed implementation roadmap for the following AI use case in the {industry} industry:
        
        {use_case_context}
        
        Provide a comprehensive implementation plan in JSON format, without JSON backticks:
        {{
            "phases": [
                {{
                    "name": "Phase name",
                    "duration": "Expected duration (e.g., 2-3 months)",
                    "activities": ["Activity 1", "Activity 2"],
                    "deliverables": ["Deliverable 1", "Deliverable 2"],
                    "resources_needed": ["Resource 1", "Resource 2"],
                    "key_stakeholders": ["Stakeholder 1", "Stakeholder 2"],
                    "risks": ["Risk 1", "Risk 2"],
                    "success_metrics": ["Metric 1", "Metric 2"]
                }}
            ],
            "estimated_timeline": "Overall timeline (e.g., 9-12 months)",
            "key_dependencies": ["Dependency 1", "Dependency 2"],
            "implementation_challenges": ["Challenge 1", "Challenge 2"],
            "success_criteria": ["Criterion 1", "Criterion 2"]
        }}
        
        Include 3-4 phases (e.g., Planning, Development, Testing, Deployment), with realistic timelines and resource requirements.
        """
        
        response = self._llm.invoke([HumanMessage(content=planning_prompt)])
        
        try:
            # Extract JSON from response
            content = response.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                plan_json = content[start_idx:end_idx]
                plan = eval(plan_json)  # Using eval instead of json.loads for flexibility
                return plan
            return {}
        except Exception as e:
            print(f"Error parsing implementation plan: {e}")
            return {}
    
    def _run(self, state: ResearchState) -> ResearchState:
        # Generate implementation plans for each use case
        implementation_plans = []
        
        for use_case in state['use_cases']:
            plan = self._create_implementation_plan(use_case, state['industry'])
            implementation_plans.append({
                "use_case": use_case.get('case', ''),
                "plan": plan
            })
        

        state['implementation_plans'] = implementation_plans
        
        return state