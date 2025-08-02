from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
from state import ResearchState
from langchain_core.messages import HumanMessage, SystemMessage

class AIRecommendationTool(BaseTool):
    name: str = "ai_recommendation"
    description: str = "Recommend AI solutions based on company needs"

    def __init__(self, llm: ChatGroq):
        super().__init__()
        self._llm = llm

    def _run(self, state: ResearchState) -> ResearchState:
        system_prompt = '''You are an AI strategy consultant specialized in helping businesses identify the most beneficial AI technologies for their specific needs. Your expertise includes:

1. Deep understanding of the current AI technology landscape across various industries
2. Ability to match business requirements with appropriate AI capabilities
3. Knowledge of implementation challenges, costs, and ROI considerations
4. Awareness of emerging AI trends and their potential business applications

When recommending AI tools, you should:
- Prioritize solutions that address critical business needs rather than trending technologies without clear applications
- Consider the company's scale, technical capabilities, and industry context
- Provide specific product names or model types (not just general categories)
- Explain concrete benefits and potential use cases for each recommendation
- Address potential implementation challenges and resource requirements
- Include both established solutions and emerging technologies when appropriate

Your recommendations should be actionable, practical, and tailored to the specific business context provided.'''
        user_prompt = f'''As an AI strategy consultant, evaluate {state['company_name']}'s potential for AI integration based on the following information:

### Company Information
- Company Name: {state['company_name']}
- Industry: {state['industry']}


### Business Profile
- Key Offerings: {', '.join(state['key_offerings'])}


### Market Context
- Industry Trends: {', '.join(state['market_trends'])}

## Deliverable
Provide a strategic AI adoption plan including:

1. Top 5 Recommended AI Technologies
For each recommendation, include:
   - Specific technology/model name
   - Primary business application
   - Expected benefits (quantitative where possible)
   - Implementation complexity (Low/Medium/High)
   - Estimated timeline for implementation
   - Potential ROI indicators

Give the output in Structured markdown format. Use bullet points for clarity and ensure the response is concise and actionable. Avoid generic recommendations and focus on technologies that are relevant to the company's specific needs and industry trends.
Focus your recommendations on technologies that align with both the company's specific needs and relevant industry trends. Include a mix of established AI solutions and emerging technologies where appropriate.'''
        messages = [
            SystemMessage(
                content=system_prompt
            ),
            HumanMessage(
                content=user_prompt
            )
         ]
        response = self._llm.invoke(messages)
        # print(response.content)
        # recommendations = response.content.split('\n')
        # recommendations = [r.strip("-• ") for r in recommendations if r.strip()]
        state['ai_recommendations'] = (response.content)
        return state
