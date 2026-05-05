from typing import Callable
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from Tools.industryResearchTool import IndustryResearchTool
from Tools.resourceCollectorTool import ResourceCollectorTool
from Tools.useCaseGeneratorTool import UseCaseGeneratorTool
from Tools.webSearchTool import WebSearchTool
from Tools.aiRecommendationTool import AIRecommendationTool
from Tools.competitorAnalysisTool import CompetitorAnalysisTool
from Tools.costBenefitTool import CostBenefitTool
from Tools.implementationPlanningTool import ImplementationPlanningTool
from state import ResearchState
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import time
def create_research_workflow(groq_api_key: str, tavily_api_key: str, progress_callback=None) -> Callable:
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        temperature=0.3,
        model_name="llama-3.3-70b-versatile",
    )
    # llm = ChatOpenAI(
    #     model="meta-llama/llama-3.3-8b-instruct:free",
    #     temperature=0.3,
    #     base_url="https://openrouter.ai/api/v1", openai_api_key=""
    # )

    web_search_tool = WebSearchTool(tavily_api_key)
    industry_research_tool = IndustryResearchTool(llm, web_search_tool)
    use_case_generator_tool = UseCaseGeneratorTool(llm)
    resource_collector_tool = ResourceCollectorTool(web_search_tool)
    # swot_analysis_tool = SWOTAnalysisTool(llm)
    ai_recommendation_tool = AIRecommendationTool(llm)
    cost_benefit_tool = CostBenefitTool(llm)
    competitor_analysis_tool = CompetitorAnalysisTool(llm, web_search_tool)
    implementation_plan_tool = ImplementationPlanningTool(llm)
    
    # Create wrapper functions that include progress callbacks
    def industry_research_with_progress(state):
        if progress_callback:
            progress_callback("🔍 Researching industry trends and company info...", 1, 8)
        result = industry_research_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Industry research completed", 1, 8)
        return result
    
    
    def use_case_generation_with_progress(state):
        if progress_callback:
            progress_callback("💡 Generating AI use cases...", 3, 8)
        result = use_case_generator_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Use cases generated", 3, 8)
        return result
    
    def ai_recommendation_with_progress(state):
        if progress_callback:
            progress_callback("🤖 Creating AI recommendations...", 4, 8)
        result = ai_recommendation_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ AI recommendations completed", 4, 8)
        return result
    
    def resource_collection_with_progress(state):
        if progress_callback:
            progress_callback("📚 Collecting relevant resources...", 5, 8)
        result = resource_collector_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Resources collected", 5, 8)
        return result
    
    def competitor_analysis_with_progress(state):
        if progress_callback:
            progress_callback("🏁 Analyzing competitors...", 6, 8)
        result = competitor_analysis_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Competitor analysis completed", 6, 8)
        return result
    
    def implementation_plan_with_progress(state):
        if progress_callback:
            progress_callback("🛠️ Creating implementation plans...", 7, 8)
        result = implementation_plan_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Implementation plans created", 7, 8)
        return result
    
    def cost_benefit_with_progress(state):
        if progress_callback:
            progress_callback("💰 Calculating cost-benefit analysis...", 8, 8)
        result = cost_benefit_tool._run(state)
        time.sleep(2)
        if progress_callback:
            progress_callback("✅ Cost-benefit analysis completed", 8, 8)
        return result
    
    workflow = StateGraph(ResearchState)
    workflow.add_node("industry_research", industry_research_with_progress)
    # workflow.add_node("swot_analysis_node", swot_analysis_with_progress)
    workflow.add_node("use_case_generation", use_case_generation_with_progress)
    workflow.add_node("ai_recommendation_node", ai_recommendation_with_progress)
    workflow.add_node("resource_collection", resource_collection_with_progress)
    workflow.add_node("competitor_analysis", competitor_analysis_with_progress)
    workflow.add_node("implementation_plan", implementation_plan_with_progress)
    workflow.add_node("cost_benefit", cost_benefit_with_progress)

    workflow.set_entry_point("industry_research")
    
    # workflow.add_edge("industry_research", "swot_analysis_node")
    # workflow.add_edge("swot_analysis_node", "use_case_generation")
    workflow.add_edge("industry_research", "use_case_generation")
    workflow.add_edge("use_case_generation", "ai_recommendation_node")
    workflow.add_edge("ai_recommendation_node", "resource_collection")
    workflow.add_edge("resource_collection", "competitor_analysis")
    workflow.add_edge("competitor_analysis", "implementation_plan")
    workflow.add_edge("implementation_plan", "cost_benefit")
    workflow.add_edge("cost_benefit", END)

    return workflow.compile()
