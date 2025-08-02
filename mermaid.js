flowchart TD
    %% Presentation Layer
    subgraph "Presentation Layer"
        UI["Streamlit UI<br/>(Login/Register, Sidebar, Tabs, Charts)"]:::frontend
        Auth["Session/Auth Manager<br/>(Remember Me, SHA-256)"]:::frontend
    end

    %% Orchestration Layer
    subgraph "Orchestration Layer"
        Orchestrator["Workflow Orchestrator<br/>LangGraph (workflow.py)"]:::orchestrator
    end

    %% Multi-Agent Workflow
    subgraph "Multi-Agent Workflow"
        Industry["IndustryResearchAgent"]:::agent
        UseCase["UseCaseGeneratorAgent"]:::agent
        AIRec["AIRecommendationAgent"]:::agent
        Resource["ResourceCollectorAgent"]:::agent
        Competitor["CompetitorAnalysisAgent"]:::agent
        Implementation["ImplementationPlanningAgent"]:::agent
        CostBenefit["CostBenefitAgent"]:::agent
        WebSearch["Web Search Agent<br/>(Tavily)"]:::agent
    end

    %% Data Persistence
    subgraph "Data Persistence"
        State["Shared ResearchState<br/>(state.py)"]:::database
        DB["SQLite Database"]:::database
    end

    %% External Services
    subgraph "External Services"
        LLM["OpenRouter / Local LM Studio"]:::external
        Tavily["Tavily API"]:::external
    end

    %% Reporting
    subgraph "Reporting"
        Charts["Plotly Charts"]:::reporting
        PDF["PDF Exporter<br/>(FPDF/ReportLab)"]:::reporting
    end

    %% User interaction
    User[/"User"/] --> UI
    UI -->|"start_research"| Orchestrator
    UI -->|reads session| Auth

    %% Orchestration to Agents
    Orchestrator --> Industry
    Orchestrator --> UseCase
    Orchestrator --> AIRec
    Orchestrator --> Resource
    Orchestrator --> Competitor
    Orchestrator --> Implementation
    Orchestrator --> CostBenefit

    %% Agents interactions
    Industry -->|calls LLM| LLM
    Industry -->|calls Tavily| Tavily
    Industry -->|writes| State
    UseCase -->|calls LLM| LLM
    UseCase -->|writes| State
    AIRec -->|calls LLM| LLM
    AIRec -->|writes| State
    Resource -->|calls Tavily| Tavily
    Resource -->|writes| State
    Competitor -->|calls LLM| LLM
    Competitor -->|writes| State
    Implementation -->|calls LLM| LLM
    Implementation -->|writes| State
    CostBenefit -->|calls LLM| LLM
    CostBenefit -->|writes| State

    %% State and DB caching
    State -->|cache as needed| DB
    Orchestrator -->|reads/writes| State

    %% UI rendering
    UI -->|reads results| State
    UI --> Charts
    UI --> PDF
    PDF --> State

    %% Click Events
    click UI "https://github.com/todap/multiagent-research/blob/main/app1.py"
    click Auth "https://github.com/todap/multiagent-research/blob/main/state.py"
    click Orchestrator "https://github.com/todap/multiagent-research/blob/main/workflow.py"
    click Industry "https://github.com/todap/multiagent-research/blob/main/Tools/industryResearchTool.py"
    click UseCase "https://github.com/todap/multiagent-research/blob/main/Tools/useCaseGeneratorTool.py"
    click AIRec "https://github.com/todap/multiagent-research/blob/main/Tools/aiRecommendationTool.py"
    click Resource "https://github.com/todap/multiagent-research/blob/main/Tools/resourceCollectorTool.py"
    click Competitor "https://github.com/todap/multiagent-research/blob/main/Tools/competitorAnalysisTool.py"
    click Implementation "https://github.com/todap/multiagent-research/blob/main/Tools/implementationPlanningTool.py"
    click CostBenefit "https://github.com/todap/multiagent-research/blob/main/Tools/costBenefitTool.py"
    click WebSearch "https://github.com/todap/multiagent-research/blob/main/Tools/webSearchTool.py"

    %% Styles
    classDef frontend fill:#f9f,stroke:#333,stroke-width:1px
    classDef orchestrator fill:#bbf,stroke:#333,stroke-width:1px
    classDef agent fill:#bfb,stroke:#333,stroke-width:1px
    classDef database fill:#fbf,stroke:#333,stroke-width:1px
    classDef external fill:#ffb,stroke:#333,stroke-width:1px
    classDef reporting fill:#fbb,stroke:#333,stroke-width:1px