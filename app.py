import streamlit as st
import os
import tempfile
import subprocess
from dotenv import load_dotenv
from agent.core import PatchworkAgent

# Load environment variables
load_dotenv()

# Configure Streamlit page (Dark Theme)
st.set_page_config(
    page_title="Patchwork-AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS to make it look highly professional and "hacker" style
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #C9D1D9;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2EA043;
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: #010409;
        color: #C9D1D9;
        border: 1px solid #30363D;
    }
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
    }
    .stCodeBlock {
        background-color: #161B22;
        border: 1px solid #30363D;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Patchwork-AI: Autonomous Engineer")
st.markdown("**Automated Code Analysis, Bug Fixing, and Pull Request Generation.**")
st.markdown("---")

# Initialize Session State
if 'agent' not in st.session_state:
    st.session_state.agent = PatchworkAgent()
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'proposed_fixes' not in st.session_state:
    st.session_state.proposed_fixes = []
if 'pr_url' not in st.session_state:
    st.session_state.pr_url = None

col1, col2 = st.columns([3, 1])
with col1:
    repo_url = st.text_input("🔗 Enter GitHub Repository URL", placeholder="https://github.com/Arpita11278/Patchwork-AI")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Analyze Repository", use_container_width=True):
        if not repo_url:
            st.warning("Please enter a valid GitHub URL.")
        else:
            # Reset state
            st.session_state.proposed_fixes = []
            st.session_state.analysis_done = False
            st.session_state.pr_url = None
            
            with st.spinner("🌐 Cloning repository securely..."):
                temp_dir = tempfile.mkdtemp(prefix="patchwork_")
                st.session_state.temp_dir = temp_dir
                subprocess.run(["git", "clone", repo_url, temp_dir], capture_output=True, text=True)
                
            with st.spinner("🔍 AI is scanning and analyzing your code..."):
                scanned_files = st.session_state.agent.scan_repository_files(temp_dir)
                issues = st.session_state.agent.analyze_code_quality(scanned_files)
                
            if not issues:
                st.success("✅ No issues found! Your code is perfect.")
            else:
                with st.spinner(f"🛠️ Generating precise AI fixes for {len(issues)} files..."):
                    for issue in issues:
                        fixed_code = st.session_state.agent.fix_with_llm(issue["content"], issue["issue"])
                        if fixed_code and fixed_code != issue["content"]:
                            st.session_state.proposed_fixes.append({
                                "file": issue["file"],
                                "issue": issue["issue"],
                                "original": issue["content"],
                                "fixed": fixed_code
                            })
                st.session_state.analysis_done = True
                st.rerun()

# Display Results
if st.session_state.analysis_done and st.session_state.proposed_fixes:
    st.subheader("⚠️ Detected Issues & Proposed AI Fixes")
    
    for i, fix in enumerate(st.session_state.proposed_fixes):
        relative_path = os.path.relpath(fix["file"], st.session_state.temp_dir)
        with st.expander(f"📄 {relative_path} - {fix['issue']}", expanded=True):
            col_orig, col_fix = st.columns(2)
            with col_orig:
                st.markdown("**❌ Original Code**")
                st.code(fix["original"], language="python")
            with col_fix:
                st.markdown("**✅ AI Proposed Fix**")
                st.code(fix["fixed"], language="python")
                
    st.markdown("---")
    st.markdown("### 🛑 Human-in-the-Loop Approval")
    
    if st.session_state.pr_url:
        st.success(f"🎉 **Pull Request Successfully Created!**")
        st.markdown(f"[👉 Click here to view your PR on GitHub]({st.session_state.pr_url})")
    else:
        if st.button("✅ Approve All Fixes & Create Pull Request"):
            with st.spinner("📤 Applying fixes and generating Pull Request on GitHub..."):
                # 1. Apply patches to the local temp files
                for fix in st.session_state.proposed_fixes:
                    with open(fix["file"], 'w', encoding='utf-8') as f:
                        f.write(fix["fixed"])
                
                # 2. Create the Pull Request via the agent
                pr_url = st.session_state.agent.create_pull_request(st.session_state.temp_dir, repo_url)
                
                if pr_url:
                    st.session_state.pr_url = pr_url
                    st.rerun()
                else:
                    st.error("❌ Failed to create PR. Please check your GITHUB_TOKEN in .env and ensure it has 'repo' permissions.")
