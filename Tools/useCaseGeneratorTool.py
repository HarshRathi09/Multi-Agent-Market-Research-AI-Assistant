import re
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from state import ResearchState, UseCase
import logging

logger = logging.getLogger(__name__)

class UseCaseGeneratorTool(BaseTool):
    name: str = "use_case_generator"
    description: str = "Generate AI/ML use cases based on research"

    def __init__(self, llm: ChatGroq):
        super().__init__()
        self._llm = llm

    def _run(self, state: ResearchState) -> ResearchState:
        logger.debug(f"Generating use cases for {state['company_name']}")
        
        # Filter the most relevant web search results based on relevance score
        web_results = sorted(
            state.get('web_search_results', []), 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )[:5]
        
        # Build the context from web search results
        web_context = "\n\n".join([
            f"Source: {result.get('title', 'No Title')}\nURL: {result.get('url', '#')}\nInsight: {result.get('content', 'No content')[:300]}..."
            for result in web_results
        ])

        # Build a detailed prompt with industry-specific guidance
        prompt = f"""
        Generate 3-5 innovative AI/ML use cases for {state['company_name']} in the {state['industry']} industry.

        Company Information:
        - Company: {state['company_name']}
        - Industry: {state['industry']}
        - Key Offerings: {', '.join(state.get('key_offerings', ['Products', 'Services']))}

        Market Context:
        {web_context}

        Market Trends:
        {', '.join(state.get('market_trends', ['Industry growth', 'Digital transformation']))}

        For each use case:
        1. Create a clear, specific title for the use case.
        2. Provide a concrete business objective that the use case addresses.
        3. Describe precisely how AI/ML will be applied (specific techniques and implementation approach).
        4. List 3-5 cross-functional benefits across different departments.
        5. Include reference links to articles (using URLs).

        Format each use case like this example:

        Use Case 1: Predictive Maintenance System
        Objective/Use Case: Reduce equipment downtime by 40% by implementing predictive maintenance for manufacturing equipment.
        AI Application: Deploy an ensemble of LSTM neural networks and random forests to analyze sensor data streams, detect anomalies, and predict potential failures 2-3 weeks before they occur.
        Cross-Functional Benefits:
        - Operations: Reduce unplanned downtime by 40% and extend equipment lifespan by 25%
        - Finance: Decrease maintenance costs by 30% and improve capital expense planning
        - Supply Chain: Optimize inventory of spare parts based on predictive insights
        - Quality: Reduce defects from degrading equipment by 15%
        Articles: https://example.com/article1, https://example.com/article2
        """

        # Create a specialized system message for better results
        system_message = SystemMessage(content=f"""
        You are an AI/ML solution architect specializing in the {state['industry']} industry. 
        Your expertise is creating specific, high-value AI/ML use cases for businesses based on their market context.
        
        Focus on practical, implementable use cases with clear business impact. Be specific about AI techniques.
        Your use cases should be innovative but achievable with current technology.
        
        For {state['company_name']}, tailor your recommendations to their specific offerings and industry position.
        Format your response exactly as specified in the prompt.
        """)

        human_message = HumanMessage(content=prompt)
        
        try:
            response = self._llm.invoke([system_message, human_message])
            
            # Extract use cases using regex pattern matching
            use_cases = self._extract_use_cases(response.content)
            
            # Update state with the extracted use cases
            state['use_cases'] = use_cases
            
            # Extract all URLs mentioned to use as resource links
            all_urls = self._extract_all_urls(response.content)
            state['resource_links'] = list(set(all_urls))
            
            logger.debug(f"Generated {len(use_cases)} use cases")
            return state
            
        except Exception as e:
            logger.error(f"Error generating use cases: {str(e)}")
            state['errors'].append(f"Use case generation error: {str(e)}")
            state['use_cases'] = []
            return state

    def _extract_use_cases(self, content: str) -> List[Dict[str, Any]]:
        """Extract structured use cases from LLM response with improved regex"""
        use_cases = []
        
        # First, split the content into separate use case sections
        case_pattern = r'Use Case \d+:.*?(?=Use Case \d+:|$)'
        case_sections = re.findall(case_pattern, content, re.DOTALL)
        
        for section in case_sections:
            try:
                # Extract components with more robust patterns
                case_title_match = re.search(r'Use Case \d+:\s*(.*?)(?:\n|$)', section)
                objective_match = re.search(r'Objective/Use Case:\s*(.*?)(?:\n|$)', section)
                ai_app_match = re.search(r'AI Application:\s*(.*?)(?:\n|$)', section)
                
                # Extract benefits as a list
                benefits = []
                benefits_section = re.search(r'Cross-Functional Benefits:(.*?)(?:Articles:|$)', section, re.DOTALL)
                if benefits_section:
                    # Extract each benefit line
                    benefit_lines = re.findall(r'-\s*(.*?)(?:\n|$)', benefits_section.group(1))
                    benefits = [line.strip() for line in benefit_lines if line.strip()]
                
                # Extract articles/URLs
                articles = []
                articles_match = re.search(r'Articles:\s*(.*?)(?:\n|$)', section)
                if articles_match:
                    # Split by commas and clean up
                    articles_text = articles_match.group(1)
                    # Extract URLs using regex
                    url_pattern = r'https?://[^\s,]+'
                    articles = re.findall(url_pattern, articles_text)
                
                # Create the use case dictionary with validation
                use_case = {
                    "case": case_title_match.group(1).strip() if case_title_match else f"Use Case {len(use_cases) + 1}",
                    "objective": objective_match.group(1).strip() if objective_match else "Improve business processes",
                    "ai_application": ai_app_match.group(1).strip() if ai_app_match else "Apply machine learning techniques",
                    "cross_functional_benefit": benefits if benefits else ["Improved efficiency"],
                    "articles": articles
                }
                
                use_cases.append(use_case)
                
            except Exception as e:
                logger.error(f"Error parsing use case section: {str(e)}")
                continue
        
        # If no use cases were successfully extracted, create a default one
        if not use_cases:
            logger.warning("No use cases extracted, creating default")
            use_cases = [{
                "case": "AI-Powered Process Optimization",
                "objective": f"Improve operational efficiency for {content[:50]}...",
                "ai_application": "Machine learning algorithms for process optimization",
                "cross_functional_benefit": ["Improved efficiency", "Cost reduction"],
                "articles": []
            }]
        
        return use_cases

    def _extract_all_urls(self, content: str) -> List[str]:
        """Extract all URLs from content"""
        url_pattern = r'https?://[^\s,)]+'
        return re.findall(url_pattern, content)