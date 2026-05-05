import streamlit as st
import os
import io
import hashlib
import time
import concurrent.futures
import pandas as pd
from dotenv import load_dotenv
from workflow import create_research_workflow
from fpdf import FPDF
import matplotlib.pyplot as plt
import sqlite3
import uuid
from datetime import datetime, timedelta
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
import markdown
import logging
import plotly.express as px
import plotly.graph_objects as go
import requests
from streamlit_lottie import st_lottie

# Set up logging
logging.basicConfig(level=logging.INFO)

# --- Database Setup ---
def init_db():
    """Initialize the SQLite database for user authentication and report caching"""
    conn = sqlite3.connect('research_app.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create users table if it doesn't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create report cache table
    c.execute('''
    CREATE TABLE IF NOT EXISTS report_cache (
        id TEXT PRIMARY KEY,
        company TEXT NOT NULL,
        industry TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if admin user exists, if not create default admin
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_id = str(uuid.uuid4())
        # Default password is 'admin123' - you should change this in production
        default_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                 (admin_id, 'admin', default_password, datetime.now()))
    
    conn.commit()
    return conn

# --- User Authentication ---
def get_password_hash(password):
    """Create SHA-256 hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    """Verify username and password"""
    conn = init_db()
    c = conn.cursor()
    
    password_hash = get_password_hash(password)
    c.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", 
             (username, password_hash))
    result = c.fetchone()
    conn.close()
    
    return result is not None

def create_user(username, password):
    """Create a new user"""
    conn = init_db()
    c = conn.cursor()
    
    try:
        user_id = str(uuid.uuid4())
        password_hash = get_password_hash(password)
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                 (user_id, username, password_hash, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False



def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

def login_page():
    st.markdown("""
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
        }
        .login-card {
            background: linear-gradient(135deg, #e0f7fa, #f8f9fa);
            padding: 3rem 2rem;
            border-radius: 15px;
            box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1);
            max-width: 420px;
            margin: auto;
        }
        input {
            border-radius: 8px !important;
        }
        .stTextInput > div > div > input {
            padding: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    lottie_login = load_lottie_url("https://assets4.lottiefiles.com/packages/lf20_jcikwtux.json")
    
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)
    st.title("🔐 AI Research Login")

    if lottie_login:
        st_lottie(lottie_login, speed=1, width=200, height=150, key="login_lottie")

    tabs = st.tabs(["Login", "Register"])

    with tabs[0]:
        username = st.text_input("👤 Username", key="login_username")
        password = st.text_input("🔑 Password", type="password", key="login_password")
        remember = st.checkbox("Remember Me")
        login = st.button("🚪 Login")

        if login:
            if authenticate(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['login_time'] = datetime.now()
                st.session_state['remember_me'] = remember
                st.success("Welcome back!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    with tabs[1]:
        new_username = st.text_input("🆕 Create Username", key="reg_username")
        new_password = st.text_input("🔒 Create Password", type="password", key="reg_password")
        confirm_password = st.text_input("✅ Confirm Password", type="password", key="confirm_password")
        register = st.button("📝 Register")

        if register:
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            elif create_user(new_username, new_password):
                st.success("🎉 Registration successful! Please login.")
            else:
                st.warning("Username already taken. Try another.")

    st.markdown("</div>", unsafe_allow_html=True)

# --- Cache Management ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_report(company, industry):
    """Retrieve a cached report if available"""
    conn = init_db()
    c = conn.cursor()
    
    c.execute("SELECT data FROM report_cache WHERE company = ? AND industry = ? AND created_at > ?", 
             (company, industry, datetime.now() - timedelta(days=1)))  # Reports valid for 1 day
    result = c.fetchone()
    conn.close()
    
    if result:
        return eval(result[0])  # Convert string representation back to dict
    return None

def cache_report(company, industry, data):
    """Cache a report for future use"""
    conn = init_db()
    c = conn.cursor()
    
    cache_id = str(uuid.uuid4())
    c.execute("INSERT INTO report_cache VALUES (?, ?, ?, ?, ?)", 
             (cache_id, company, industry, str(data), datetime.now()))
    conn.commit()
    conn.close()

# --- PDF Export with Unicode Support ---
class UnicodeSupport(FPDF):
    """Custom FPDF class with Unicode support"""
    def __init__(self):
        super().__init__()
        # Add DejaVu font for better Unicode support
        self.add_font('DejaVu', '', '/System/Library/Fonts/Arial Unicode.ttf', uni=True)
        self.add_font('DejaVu', 'B', '/System/Library/Fonts/Arial Unicode.ttf', uni=True)
        self.add_font('DejaVu', 'I', '/System/Library/Fonts/Arial Unicode.ttf', uni=True)
    
    def header(self):
        # This method is called before rendering a page
        self.set_font('DejaVu', 'B', 10)
        self.cell(0, 10, 'AI Research Report', 0, 1, 'R')
        self.ln(5)
    
    def footer(self):
        # This method is called at the end of each page
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(company, result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def clean_text(text):
        return ''.join(c if ord(c) < 128 else ' ' for c in str(text))

    def section_title(title):
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_draw_color(0, 0, 0)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    def write_bullets(items):
        pdf.set_font("Arial", size=11)
        for item in items:
            pdf.multi_cell(0, 8, f"- {clean_text(item)}")
        pdf.ln(2)

    # ---------------- HEADER ----------------
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, f"{company} Research Report", ln=True, align='C')

    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')

    pdf.ln(10)

    # ---------------- SECTIONS ----------------
    section_title("1. Key Offerings")
    write_bullets(result.get("key_offerings", []))

    section_title("2. Market Trends")
    write_bullets(result.get("market_trends", []))

    section_title("3. AI Recommendations")
    write_bullets(result.get("ai_recommendations", []))

    # ---------------- USE CASES ----------------
    section_title("4. AI/ML Use Cases")

    for i, uc in enumerate(result.get("use_cases", []), 1):
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 8, f"{i}. {clean_text(uc.get('case', ''))}")

        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 7, f"Objective: {clean_text(uc.get('objective', ''))}")
        pdf.multi_cell(0, 7, f"AI Application: {clean_text(uc.get('ai_application', ''))}")

        pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 7, "Benefits:")

        pdf.set_font("Arial", size=11)
        for b in uc.get("cross_functional_benefit", []):
            pdf.multi_cell(0, 7, f"   - {clean_text(b)}")

        if uc.get("articles"):
            pdf.set_font("Arial", 'I', 11)
            pdf.multi_cell(0, 7, "References:")
            pdf.set_font("Arial", size=10)
            for link in uc["articles"]:
                pdf.multi_cell(0, 6, f"   - {link}")

        pdf.ln(4)

    # ---------------- OTHER SECTIONS ----------------
    section_title("5. Implementation Plans")

    for plan in result.get("implementation_plans", []):
        pdf.set_font("Arial", 'B', 12)
        pdf. multi_cell(0, 8, clean_text(plan.get("use_case", "")))
        pdf.set_font("Arial", size=11)
        phases = plan.get("plan", {}).get("phases", [])
    
        for p in phases:
            pdf.set_font("Arial", 'I', 11)
            pdf.multi_cell(0, 7, f"Phase: {clean_text(p.get('name', ''))}")       
            pdf.set_font("Arial", size=10)
        for act in p.get("activities", []):
            pdf.multi_cell(0, 6, f"  - {clean_text(act)}")

    pdf.ln(4)

     
    # ---------------- FOOTER ----------------
    pdf.set_y(-15)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Page {pdf.page_no()}", align='C')

    return pdf.output(dest='S').encode('latin1')

# --- Alternative PDF using BytesIO ---
def create_pdf_safe(company, result):
    """Safe alternative PDF creation that handles Unicode characters better"""
    try:
        import io
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1,  # Center alignment
            spaceAfter=12
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Title
        elements.append(Paragraph(f"Research Report: {company}", title_style))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Italic"]))
        elements.append(Spacer(1, 20))
        
        def add_section(title, items):
            elements.append(Paragraph(title, subtitle_style))
            
            if isinstance(items, list):
                for item in items:
                    elements.append(Paragraph(f"• {item}", body_style))
            else:
                elements.append(Paragraph(str(items), body_style))
            
            elements.append(Spacer(1, 10))
        
        # Add content sections
        add_section("Key Offerings", result['key_offerings'])
        add_section("Market Trends", result['market_trends'])
        # add_section("Opportunities", result['swot_analysis']['opportunities'])
        # add_section("Threats", result['swot_analysis']['threats'])
        add_section("AI Recommendations", markdown.markdown(result['ai_recommendations']))
        add_section("Use Cases", result['use_cases'])
        add_section("Implementation Plans", result['implementation_plans'])
        add_section("Cost-Benefit Analysis", result['cost_benefit_analyses'])
        add_section("Competitor Analysis", result['competitor_analysis_tool'])
        add_section("Competitors", result['competitors'])

        
        # Build the PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    except Exception as e:
        # If ReportLab fails, try a very simple FPDF with minimal content
        st.error(f"PDF generation error: {e}")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Research Report: {company}", ln=True, align='C')
        pdf.cell(0, 10, "Error generating PDF with special characters.", ln=True)
        
        return pdf.output(dest='S').encode('latin1')

# --- Async Research Function ---
def research_company(workflow, company, industry, progress_callback=None):
    """Research a single company with detailed progress updates"""
    # First check cache
    cached_result = get_cached_report(company, industry)
    if cached_result:
        if progress_callback:
            progress_callback("📋 Found cached result", 8, 8)
        return company, cached_result
    
    # If not in cache, perform research with status updates
    initial_state = {'company_name': company, 'industry': industry}
    
    if progress_callback:
        progress_callback("🚀 Starting research workflow...", 0, 8)
    
    result = workflow.invoke(initial_state)
    
    # Cache the result
    cache_report(company, industry, result)
    
    if progress_callback:
        progress_callback("🎉 Research completed!", 8, 8)
    
    return company, result
    
    # Cache the result
    cache_report(company, industry, result)
    
    return company, result

# --- UI Components ---
def render_sidebar():
    """Render the sidebar with user info and navigation"""
    with st.sidebar:
        # User profile section
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4e89e3 0%, #3d6db3 100%); 
                    color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;
                    text-align: center;">
            <h2 style="margin: 0;">🔍 AI Research</h2>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">👤 {st.session_state['username']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🧭 Navigation")
        page = st.radio(
            "Select page", 
            ["🔬 Company Research", "📚 Past Reports", "⚙️ Settings"],
            format_func=lambda x: x,
            label_visibility="hidden"
        )
        
        st.markdown("---")
        
        # Enhanced logout button
        if st.button("🚪 Logout", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        # Enhanced about section
        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <h4>💡 About</h4>
            <p style="font-size: 0.9em; margin: 0;">
                This tool uses advanced AI to analyze companies and industries, 
                providing comprehensive insights and recommendations.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("© 2025 AI Research Assistant")
    
    # Clean up the page name for logic
    page = page.split(" ", 1)[1]  # Remove emoji prefix
    return page
    
    return page

def display_company_tab(company, result):
    """Display a single company's research results in a tab"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #4e89e3 0%, #3d6db3 100%); 
                color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px;
                box-shadow: 0 4px 8px rgba(78, 137, 227, 0.3);">
        <h1 style="margin: 0; display: flex; align-items: center;">
            <span style="margin-right: 15px;">🏢</span>{company}
        </h1>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">AI-Powered Company Analysis Report</p>
    </div>
    """, unsafe_allow_html=True)
    st.header(f"📊 {company}")
    
    # Create columns for key data
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 Key Offerings")
        for item in result['key_offerings']:
            st.markdown(f"• {item}")
    
    with col2:
        st.subheader("📈 Market Trends")
        for item in result['market_trends']:
            st.markdown(f"• {item}")
    
    
    # AI Recommendations with styled background
    with st.container():
        st.markdown("""
        <style>
        .ai-container {
            background-color: #f0f7ff;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            border-left: 5px solid #3498db;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="ai-container">', unsafe_allow_html=True)
        st.subheader("🤖 AI Recommendations")
        # for item in result['ai_recommendations']:
        st.markdown(result['ai_recommendations'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Use Cases
    st.subheader("📋 Use Cases")
    use_cases = result['use_cases']
    for i, use_case in enumerate(use_cases):
        with st.expander(f"Use Case {i+1}: {use_case['case']}"):
            st.markdown(f"**Objective:** {use_case['objective']}")
            st.markdown(f"**AI Application:** {use_case['ai_application']}")
            st.markdown(f"**Cross-Functional Benefits:** {use_case['cross_functional_benefit']}")
            st.markdown(f"**Articles:** {use_case['articles']}")

    # Implementation Plan
    st.subheader("🛠️ Implementation Plan")
    for use_case_data in result['implementation_plans']:
        use_case = use_case_data['use_case']
        plan = use_case_data['plan']
        
        st.header(f"Use Case: {use_case}")

        for i, phase in enumerate(plan['phases']):
            with st.expander(f"Phase {i+1}: {phase['name']}"):
                st.markdown(f"**Duration:** {phase['duration']}")
                st.markdown(f"**Activities:** {', '.join(phase['activities'])}")
                st.markdown(f"**Deliverables:** {', '.join(phase['deliverables'])}")
                st.markdown(f"**Resources Needed:** {', '.join(phase['resources_needed'])}")
                st.markdown(f"**Key Stakeholders:** {', '.join(phase['key_stakeholders'])}")
                st.markdown(f"**Risks:** {', '.join(phase['risks'])}")
                st.markdown(f"**Success Metrics:** {', '.join(phase['success_metrics'])}")

        # Display overall implementation plan metadata outside the loop
        st.subheader("Overall Implementation Plan Details")
        st.markdown(f"**Estimated Timeline:** {plan['estimated_timeline']}")
        st.markdown(f"**Key Dependencies:** {', '.join(plan['key_dependencies'])}")
        st.markdown(f"**Implementation Challenges:** {', '.join(plan['implementation_challenges'])}")
        st.markdown(f"**Success Criteria:** {', '.join(plan['success_criteria'])}")

            
    # Cost-Benefit Analysis
    st.subheader("💰 Cost-Benefit Analysis")
    def extract_percentage_range(roi_range):
        try:
            parts = roi_range.replace('%', '').split('-')
            return int(parts[0]), int(parts[1])
        except:
            return 0, 0

    for i, use_case in enumerate(result['cost_benefit_analyses']):
        case_title = use_case['use_case']
        analysis = use_case['analysis']
        
        with st.expander(f"Use Case {i+1}: {case_title}"):
            tab1, tab2, tab3, tab4 = st.tabs(["Implementation Costs", "Expected Benefits", "ROI Analysis", "Risk Factors"])

            # Tab 1 - Implementation Costs
            with tab1:
                tech = analysis['implementation_costs']['technology']
                hr = analysis['implementation_costs']['human_resources']
                other_costs = analysis['implementation_costs']['other_costs']
                total_cost = analysis['implementation_costs']['total_cost_range']

                st.markdown("### 📦 Technology Costs")
                for key, val in tech.items():
                    st.markdown(f"- **{key.replace('_', ' ').title()}**: {val}")

                st.markdown("### 👥 Human Resources Costs")
                for key, val in hr.items():
                    st.markdown(f"- **{key.replace('_', ' ').title()}**: {val}")

                st.markdown("### 📌 Other Costs")
                st.markdown(f"- {', '.join(other_costs)}")

                st.markdown(f"### 💲 **Total Cost Range:** `{total_cost}`")

            # Tab 2 - Expected Benefits
            with tab2:
                st.markdown("### 📊 Quantitative Benefits")
                benefits = analysis['expected_benefits']['quantitative']
                for benefit in benefits:
                    st.markdown(f"- **{benefit['benefit']}**: {benefit['estimated_value']} (_{benefit['timeframe']}_)")

                st.markdown("### 🌟 Qualitative Benefits")
                for benefit in analysis['expected_benefits']['qualitative']:
                    st.markdown(f"- {benefit}")

                # Visualize: Cost vs Benefit Bar Chart
                benefit_vals = []
                benefit_labels = []
                for benefit in benefits:
                    value_range = benefit['estimated_value'].replace('$', '').replace('%', '').replace(',', '').split('-')
                    benefit_labels.append(benefit['benefit'])
                    try:
                        benefit_vals.append(int(value_range[0]))  # taking min value
                    except ValueError:
                        # If not a number, skip this benefit for visualization
                        continue

                cost_range = analysis['implementation_costs']['total_cost_range'].replace('$', '').replace('%', '').replace(',', '').split('-')
                try:
                    min_cost = int(cost_range[0])
                except ValueError:
                    min_cost = 0  # Default if not parseable

                fig = go.Figure(data=[
                    go.Bar(name='Estimated Benefits', x=benefit_labels, y=benefit_vals, marker_color='green'),
                    go.Bar(name='Total Cost (Min)', x=benefit_labels, y=[min_cost] * len(benefit_vals), marker_color='red')
                ])
                fig.update_layout(barmode='group', title='📉 Cost vs. Benefit (Min Value Estimates)', yaxis_title='Amount ($)')
                st.plotly_chart(fig, use_container_width=True)

            # Tab 3 - ROI
            with tab3:
                roi = analysis['roi_analysis']
                st.markdown("### 📈 ROI Metrics")
                col1, col2, col3 = st.columns(3)
                col1.metric("Payback Period", roi['payback_period'])
                col2.metric("First Year ROI", roi['first_year_roi'])
                col3.metric("3-Year ROI", roi['three_year_roi'])

                # ROI Progress Bars
                min_roi, max_roi = extract_percentage_range(roi['first_year_roi'])
                st.markdown("#### 🔄 First Year ROI Progress")
                st.progress(min(min_roi, 100) / 100)

                st.markdown("#### 🔄 3-Year ROI Progress")
                min_roi3, _ = extract_percentage_range(roi['three_year_roi'])
                st.progress(min(min_roi3, 100) / 100)

                st.markdown("### 🚀 Non-Financial Benefits")
                for nf in roi['non_financial_benefits']:
                    st.markdown(f"- {nf}")

            # Tab 4 - Risks
            with tab4:
                st.markdown("### ⚠️ Risk Factors")
                for risk in analysis['risk_factors']:
                    st.markdown(f"- {risk}")


    # Competitor Analysis
    st.subheader("🏁 Competitor Analysis")
    analysis=result['competitor_analysis_tool']
    # Tabs
    tabs = st.tabs(["🔢 AI Maturity", "📊 Competitive Positioning", "🧠 SWOT Analysis"])

    # --- Tab 1: AI Maturity ---
    with tabs[0]:
        st.subheader("🤖 AI Maturity Overview")

        # Metric display
        st.metric(label="AI Maturity Score", value=analysis['ai_maturity_score'], delta="High")

        # Explanation block
        st.markdown(f"""
        <div style="background-color:#e0f7fa; padding:15px; border-radius:10px;">
            <p>{analysis['ai_maturity_explanation']}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- Tab 2: Competitive Positioning ---
    with tabs[1]:
        st.subheader("🏁 Competitive Positioning")

        st.markdown(f"""
        <div style="background-color:#f3e5f5; padding:15px; border-radius:10px;">
            <p>{analysis['competitive_positioning']}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- Tab 3: SWOT Analysis ---
    with tabs[2]:
        st.subheader("🧠 SWOT Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
    <div style="background-color:#d0f0c0; padding:10px; border-radius:10px;">
        <h4>✅ Strengths</h4>
    </div>
    """, unsafe_allow_html=True)
            for s in analysis['strengths']:
                st.markdown(f"- ✔️ {s}")

        with col2:
            st.markdown("""
    <div style="background-color:#ffcdd2; padding:10px; border-radius:10px;">
        <h4>⚠️ Weaknesses</h4>
    </div>
    """, unsafe_allow_html=True)
            for w in analysis['weaknesses']:
                st.markdown(f"- ❌ {w}")

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("""
    <div style="background-color:#fff9c4; padding:10px; border-radius:10px;">
        <h4>🚀 Opportunities</h4>
    </div>
    """, unsafe_allow_html=True)
            for o in analysis['opportunities']:
                st.markdown(f"- 🌟 {o}")

        with col4:
            st.markdown("""
    <div style="background-color:#f8bbd0; padding:10px; border-radius:10px;">
        <h4>🔥 Threats</h4>
    </div>
    """, unsafe_allow_html=True)
            for t in analysis['threats']:
                st.markdown(f"- ⚡ {t}")
    # Competitors
    st.subheader("🏆 Competitors")
    competitors = result['competitors']
    tabs = st.tabs([c['name'] for c in competitors])

    for i, competitor in enumerate(competitors):
        with tabs[i]:
            st.markdown(f"### 🏷️ {competitor['name']}")
            st.markdown(f"**Description:** {competitor['description']}")
            st.markdown("**AI Initiatives:**")
            for ai in competitor['ai_initiatives']:
                st.markdown(f"- 🤖 {ai}")

    # Resources
    with st.expander("📚 Resources"):
        for link in result['resource_links']:
            st.markdown(f"- [{link}]({link})")
    
    # Use try-except to attempt different PDF methods
    try:
        # Try to use ReportLab first (better Unicode support)
        pdf_bytes = create_pdf_safe(company, result)
        
        st.download_button(
            f"📄 Download {company} Report", 
            data=pdf_bytes,
            file_name=f"{company}_research_report.pdf", 
            mime="application/pdf",
            key=f"download_{company}",
            help="Download this report as a PDF document"
        )
    except ImportError:
        # Fall back to FPDF with simplified content if ReportLab not available
        try:
            pdf_bytes = create_pdf(company, result)
            
            st.download_button(
                f"📄 Download {company} Report", 
                data=pdf_bytes,
                file_name=f"{company}_research_report.pdf", 
                mime="application/pdf",
                key=f"download_{company}",
                help="Download this report as a PDF document"
            )
        except Exception as e:
            st.error(f"Could not generate PDF: {str(e)}")
            st.info("View the report online for best results.")

def display_streaming_results():
    """Display results as they become available"""
    if 'research_results' in st.session_state and st.session_state['research_results']:
        st.markdown("## Live Results")
        
        # Show results in accordion style for better organization
        for company, result in st.session_state['research_results'].items():
            with st.expander(f"📊 {company}", expanded=len(st.session_state['research_results']) == 1):
                display_company_tab(company, result)
# --- Main App ---
def main():
    """Main application function"""
    st.set_page_config(page_title="AI Research Assistant", page_icon="🔍", layout="wide")
    
    st.markdown("""
<style>
    /* Enhanced Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 10px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        border: 2px solid #e9ecef;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4e89e3 0%, #3d6db3 100%);
        color: white !important;
        border: 2px solid #3d6db3;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(78, 137, 227, 0.3);
    }
    
    /* Enhanced Cards */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        margin: 10px 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    
    /* Progress Enhancement */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4e89e3 0%, #3d6db3 100%);
        border-radius: 10px;
    }
    
    /* Form Enhancement */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 2px solid #e9ecef !important;
        padding: 12px 16px !important;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4e89e3 !important;
        box-shadow: 0 0 0 3px rgba(78, 137, 227, 0.1) !important;
    }
    
    /* Button Enhancement */
    .stButton > button {
        background: linear-gradient(135deg, #4e89e3 0%, #3d6db3 100%);
        border: none;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(78, 137, 227, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 10px rgba(78, 137, 227, 0.4);
    }
</style>
""", unsafe_allow_html=True)
    
    # Initialize database
    init_db()
    
    # Load environment variables
    load_dotenv()
    groq_api_key = os.getenv('groq_api_key')
    tavily_api_key = os.getenv('tavily_api_key')
    
    # Check if API keys are available
    if not groq_api_key or not tavily_api_key:
        st.error("❌ API keys not found. Please check your .env file.")
        return
    
    # Create workflow once
    workflow = create_research_workflow(groq_api_key, tavily_api_key)
    
    # Check login status
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        login_page()
        return
    
    # If session expired (24 hours) and not remember me
    if ('login_time' in st.session_state and 
        datetime.now() - st.session_state['login_time'] > timedelta(hours=24) and 
        not st.session_state.get('remember_me', False)):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Render sidebar and get current page
    page = render_sidebar()
    
    # Handle different pages
    if page == "Company Research":
        st.title("🔍 Company Research")
        
        # Input form
        # Enhanced input form with better styling
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        with st.form(key="input_form"):
            st.markdown("### 🚀 Start Your Research")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                company_input = st.text_input(
                    "🏢 Company Names", 
                    placeholder="e.g., Tesla, Rivian, Lucid Motors",
                    help="Enter multiple companies separated by commas"
                )
            with col2:
                industry = st.text_input(
                    "🏭 Industry", 
                    placeholder="e.g., Automotive",
                    help="Specify the industry sector"
                )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                submit = st.form_submit_button(
                    "🔍 Start Research", 
                    type="primary", 
                    use_container_width=True
                )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit:
            if not company_input or not industry:
                st.error("Please enter both company names and industry.")
                return
            
            companies = [c.strip() for c in company_input.split(",")]
            
            # Initialize session state for results
            if 'research_results' not in st.session_state:
                st.session_state['research_results'] = {}
            
            # Clear previous results
            st.session_state['research_results'] = {}
            st.session_state['last_industry'] = industry
            
            # Create progress containers
            overall_progress_container = st.container()
            detailed_progress_container = st.container()
            results_container = st.container()

            with overall_progress_container:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown("### 📊 Overall Progress")
                overall_progress = st.progress(0)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**📋 Total Companies**")
                    total_companies_display = st.empty()
                    total_companies_display.markdown(f"<h2 style='color: #4e89e3; margin: 0;'>{len(companies)}</h2>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**✅ Completed**")
                    completed_display = st.empty()
                    completed_display.markdown("<h2 style='color: #28a745; margin: 0;'>0</h2>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown("**🔄 Current**")
                    current_display = st.empty()
                    current_display.markdown("<p style='color: #6c757d; margin: 0;'>Not started</p>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Process companies sequentially with detailed progress
            for company_idx, company in enumerate(companies):
                current_display.markdown(f"<p style='color: #4e89e3; font-weight: bold; margin: 0;'>{company}</p>", unsafe_allow_html=True)
                
                with detailed_progress_container:
                    st.markdown(f"### Researching: {company}")
                    detailed_progress = st.progress(0)
                    status_text = st.empty()
                    
                    # Create workflow with progress callback
                    def progress_callback(message, step, total_steps):
                        progress = step / total_steps
                        detailed_progress.progress(progress)
                        status_text.text(f"Step {step}/{total_steps}: {message}")
                        
                        # Force Streamlit to update the UI
                        time.sleep(0.1)
                    
                    # Create workflow with callback
                    workflow_with_progress = create_research_workflow(groq_api_key, tavily_api_key, progress_callback)
                
                try:
                    # Research the company with progress tracking
                    _, result = research_company(workflow_with_progress, company, industry, progress_callback)
                    st.session_state['research_results'][company] = result
                    
                    # Update overall progress
                    overall_progress_value = (company_idx + 1) / len(companies)
                    overall_progress.progress(overall_progress_value)
                    completed_display.markdown(f"<h2 style='color: #28a745; margin: 0;'>{company_idx + 1}</h2>", unsafe_allow_html=True)
                    
                    status_text.text("✅ Research completed!")
                    detailed_progress.progress(1.0)
                    
                    # Show completed company result immediately
                    with results_container:
                        st.success(f"✅ Research completed for {company}")
                        
                        # Display each company in its own section with tabs
                        st.markdown("## Results")
                        
                        # Create a tab for each completed company
                        if len(st.session_state['research_results']) > 0:
                            company_names = list(st.session_state['research_results'].keys())
                            company_tabs = st.tabs(company_names)
                            
                            for tab_idx, (comp_name, tab) in enumerate(zip(company_names, company_tabs)):
                                with tab:
                                    display_company_tab(comp_name, st.session_state['research_results'][comp_name])
                            
                except Exception as e:
                    st.error(f"❌ Error researching {company}: {str(e)}")
                    status_text.text(f"❌ Error: {str(e)}")
                    continue
            
            # Final completion
            current_display.markdown("<p style='color: #28a745; font-weight: bold; margin: 0;'>All Complete 🎉</p>", unsafe_allow_html=True)
            
    
    elif page == "Past Reports":
        st.title("📚 Past Reports")
        
        # Get cached reports
        conn = init_db()
        c = conn.cursor()
        c.execute("SELECT company, industry, created_at FROM report_cache ORDER BY created_at DESC")
        reports = c.fetchall()
        conn.close()
        
        if not reports:
            st.info("No reports found. Research some companies to see them here.")
        else:
            # Convert to DataFrame for display
            df = pd.DataFrame(reports, columns=["Company", "Industry", "Date"])
            pd.to_datetime(..., format="mixed", errors="coerce")

            # Display header
            st.write("### Past Reports")

            # Render as table with view buttons
            for idx, row in df.iterrows():
                cols = st.columns([3, 3, 3, 1])
                cols[0].write(row["Company"])
                cols[1].write(row["Industry"])
                cols[2].write(row["Date"])
                if cols[3].button("View", key=f"view_{idx}"):
                    cached_result = get_cached_report(row["Company"], row["Industry"])
                    if cached_result:
                        st.subheader(f"Report for {row['Company']}")
                        display_company_tab(row["Company"], cached_result)
    
    elif page == "Settings":
        st.title("⚙️ Settings")
        
        st.subheader("User Settings")
        with st.expander("Change Password"):
            with st.form("Change Password"):
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                
                submit_password = st.form_submit_button("Update Password")
                
                if submit_password:
                    if not authenticate(st.session_state['username'], current_password):
                        st.error("Current password is incorrect.")
                    elif new_password != confirm_new_password:
                        st.error("New passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        conn = init_db()
                        c = conn.cursor()
                        password_hash = get_password_hash(new_password)
                        c.execute("UPDATE users SET password_hash = ? WHERE username = ?", 
                                (password_hash, st.session_state['username']))
                        conn.commit()
                        conn.close()
                        st.success("Password updated successfully!")
        
        st.subheader("Application Settings")
        with st.expander("Cache Management"):
            if st.button("Clear Cache", type="secondary"):
                conn = init_db()
                c = conn.cursor()
                c.execute("DELETE FROM report_cache")
                conn.commit()
                conn.close()
                st.success("Cache cleared successfully!")
                # Clear session state research results
                if 'research_results' in st.session_state:
                    del st.session_state['research_results']

if __name__ == "__main__":
    main()
