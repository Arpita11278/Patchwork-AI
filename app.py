import streamlit as st
import os
import shutil
import tempfile
import subprocess
from dotenv import load_dotenv
from agent.core import PatchworkAgent

# Load environment variables (.env locally or st.secrets on Streamlit Cloud)
load_dotenv()

def get_env_or_secret(key, default=None):
    if os.getenv(key):
        return os.getenv(key)
    if os.getenv(key.lower()):
        return os.getenv(key.lower())
    if os.getenv(key.upper()):
        return os.getenv(key.upper())
    try:
        if key in st.secrets:
            return str(st.secrets[key])
        if key.lower() in st.secrets:
            return str(st.secrets[key.lower()])
        if key.upper() in st.secrets:
            return str(st.secrets[key.upper()])
        for section in st.secrets:
            try:
                sec_val = st.secrets[section]
                if hasattr(sec_val, 'get'):
                    val = sec_val.get(key) or sec_val.get(key.lower()) or sec_val.get(key.upper())
                    if val:
                        return str(val)
            except Exception:
                pass
    except Exception:
        pass
    return default

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

# Verify critical environment variables
api_missing = not get_env_or_secret("OPENAI_API_KEY") and not get_env_or_secret("OPENROUTER_API_KEY")
if api_missing:
    st.error("⚠️ API Key not found! Please set OPENAI_API_KEY or OPENROUTER_API_KEY in your .env file or Streamlit Secrets.")

# Always initialize a fresh agent so it picks up code changes in core.py
agent = PatchworkAgent()

# Initialize Session State
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'proposed_fixes' not in st.session_state:
    st.session_state.proposed_fixes = []
if 'pr_url' not in st.session_state:
    st.session_state.pr_url = None
if 'pr_error' not in st.session_state:
    st.session_state.pr_error = None

def cleanup_temp_dir():
    if st.session_state.temp_dir and os.path.exists(st.session_state.temp_dir):
        shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
        st.session_state.temp_dir = None

col1, col2 = st.columns([3, 1])
with col1:
    repo_url = st.text_input("🔗 Enter GitHub Repository URL", placeholder="https://github.com/username/repository")

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Analyze Repository", use_container_width=True, disabled=api_missing):
        if not repo_url or not repo_url.startswith("https://github.com/"):
            st.warning("Please enter a valid GitHub URL starting with 'https://github.com/'.")
        else:
            # Clean up previous session
            cleanup_temp_dir()
            
            # Reset state
            st.session_state.proposed_fixes = []
            st.session_state.analysis_done = False
            st.session_state.pr_url = None
            st.session_state.pr_error = None
            
            with st.spinner("🌐 Cloning repository securely..."):
                temp_dir = tempfile.mkdtemp(prefix="patchwork_")
                st.session_state.temp_dir = temp_dir
                
                # Clone command
                result = subprocess.run(
                    ["git", "clone", repo_url, temp_dir], 
                    capture_output=True, 
                    text=True
                )
                
            if result.returncode != 0:
                st.error("❌ Failed to clone repository. Please check the URL and your access permissions.")
                with st.expander("Show Clone Error"):
                    st.code(result.stderr)
                cleanup_temp_dir()
            else:
                with st.spinner("🔍 Scanning repository files..."):
                    scanned_files = agent.scan_repository_files(temp_dir)
                    
                if not scanned_files:
                    st.warning("⚠️ No supported source code files (.py, .js, .ts, .java, .cpp) were found in this repository.")
                    cleanup_temp_dir()
                else:
                    with st.spinner(f"🔍 Analyzing {len(scanned_files)} source code files..."):
                        issues = agent.analyze_code_quality(scanned_files)
                        
                    if not issues:
                        st.success(f"✅ Analyzed {len(scanned_files)} files and no issues were found! Your code is perfectly clean.")
                        cleanup_temp_dir()
                    else:
                        # Check for API Errors first
                        api_errors = [iss for iss in issues if iss["issue"].startswith("API_ERROR:")]
                        if api_errors:
                            st.error("❌ LLM API Error occurred during analysis:")
                            st.code(api_errors[0]["issue"])
                            cleanup_temp_dir()
                        else:
                            with st.spinner(f"🛠️ Generating precise AI fixes for {len(issues)} files..."):
                                fix_api_error = None
                                for issue in issues:
                                    fixed_code = agent.fix_with_llm(issue["content"], issue["issue"])
                                    if fixed_code and fixed_code.startswith("API_ERROR:"):
                                        fix_api_error = fixed_code
                                        break
                                    if fixed_code and fixed_code != issue["content"]:
                                        st.session_state.proposed_fixes.append({
                                            "file": issue["file"],
                                            "issue": issue["issue"],
                                            "original": issue["content"],
                                            "fixed": fixed_code
                                        })
                            
                            if fix_api_error:
                                st.error("❌ LLM API Error occurred while generating fixes:")
                                st.code(fix_api_error)
                                cleanup_temp_dir()
                            else:
                                st.session_state.analysis_done = True
                                st.rerun()

# Display Results
if st.session_state.analysis_done:
    if not st.session_state.proposed_fixes:
        st.warning("⚠️ Analysis completed, but no fixes were generated. The AI may have hit a rate limit during the fix phase.")
    else:
        st.subheader("⚠️ Detected Issues & Proposed AI Fixes")
        
        for i, fix in enumerate(st.session_state.proposed_fixes):
            relative_path = os.path.relpath(fix["file"], st.session_state.temp_dir)
            
            # Count the number of issues (roughly by bullet points)
            issue_lines = [line.strip() for line in fix['issue'].split('\n') if line.strip()]
            issue_count = len([line for line in issue_lines if line.startswith('-')]) or len(issue_lines)
            
            with st.expander(f"📄 {relative_path} — ({issue_count} Issues Detected)", expanded=True):
                st.markdown(f"### 🔍 AI Analysis Found {issue_count} Issues:")
                
                # Use standard markdown instead of st.info for better readability in dark mode
                st.markdown(fix['issue'])
                st.markdown("---")
                
                col_orig, col_fix = st.columns(2)
                with col_orig:
                    st.markdown("**❌ Original Code**")
                    st.code(fix["original"], language="python")
                with col_fix:
                    st.markdown("**✅ AI Proposed Fix**")
                    st.code(fix["fixed"], language="python")
                    
        st.markdown("---")
        st.markdown("### 🛑 Human-in-the-Loop Approval")
        
        if st.session_state.pr_error:
            st.error(st.session_state.pr_error)
            
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
                    pr_url, error_msg = agent.create_pull_request(st.session_state.temp_dir, repo_url)
                    
                    if pr_url:
                        st.session_state.pr_url = pr_url
                        st.session_state.pr_error = None
                        cleanup_temp_dir()
                        st.rerun()
                    else:
                        st.session_state.pr_error = error_msg
                        st.rerun()
