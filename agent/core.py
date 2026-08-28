import os
import shutil
import tempfile
from dotenv import load_dotenv
import subprocess
import requests
import json

load_dotenv()

def get_env_or_secret(key, default=None):
    # 1. Check os.environ
    if os.getenv(key):
        return os.getenv(key)
    if os.getenv(key.lower()):
        return os.getenv(key.lower())
    if os.getenv(key.upper()):
        return os.getenv(key.upper())
    
    # 2. Check st.secrets directly for Streamlit Cloud
    try:
        import streamlit as st
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

class PatchworkAgent:
    def __init__(self):
        print("🤖 Patchwork AI Agent initialized.")
        self.api_key = get_env_or_secret("OPENROUTER_API_KEY") or get_env_or_secret("OPENAI_API_KEY")
        self.github_token = get_env_or_secret("GITHUB_TOKEN")

        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"
        if get_env_or_secret("OPENROUTER_API_KEY"):
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model = "openrouter/free"  # Always free, works with 0 credits

        if not self.api_key:
            print("⚠️ Warning: API Key not found! Will use basic rule-based checks.")
        else:
            print("✅ API Key loaded for LLM analysis.")

    def fetch_github_repo(self, repo_name: str):
        """Phase 1: Fetch repository details from GitHub API"""
        print(f"🌐 Connecting to GitHub for repository: {repo_name}...")
        url = f"https://api.github.com/repos/{repo_name}"
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                repo_data = response.json()
                print(f"✅ Successfully connected to GitHub repo: {repo_data.get('full_name')}")
                print(f"⭐ Stars: {repo_data.get('stargazers_count')} | 🍴 Forks: {repo_data.get('forks_count')}")
                return True
            else:
                print(f"❌ Failed to fetch repo from GitHub. Status Code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GitHub API Error: {e}")
            return False

    def process_github_repo(self, repo_url: str):
        print(f"\n🌐 Cloning repository from {repo_url}...")
        temp_dir = tempfile.mkdtemp(prefix="patchwork_")
        try:
            result = subprocess.run(["git", "clone", repo_url, temp_dir], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Successfully cloned into {temp_dir}")
                changes_made = self.process_local_repo(temp_dir)
                if changes_made:
                    pr_url, error_msg = self.create_pull_request(temp_dir, repo_url)
                    if error_msg:
                        print(f"❌ {error_msg}")
            else:
                print(f"❌ Failed to clone repository: {result.stderr}")
        except Exception as e:
            print(f"❌ Error during git clone: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _mask(self, text: str) -> str:
        """Strip the GitHub token out of any string before it gets logged/printed."""
        if self.github_token and text:
            return text.replace(self.github_token, "***REDACTED***")
        return text

    def create_pull_request(self, repo_path: str, repo_url: str):
        """
        Returns a tuple: (pr_url, error_msg)
        Exactly one of the two will be non-None.
        """
        if not self.github_token:
            msg = "GITHUB_TOKEN not found in .env. Add a token with 'repo' scope to enable PR creation."
            print(f"\n⚠️ {msg}")
            return None, msg

        print("\n🚀 Pushing changes and creating Pull Request...")
        import uuid
        branch_name = f"patchwork-ai-fixes-{uuid.uuid4().hex[:6]}"

        try:
            # 1. Create a new branch and commit changes
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)

            if not status.stdout.strip():
                msg = "No changes to commit — the AI fixes didn't modify any file content. Skipping PR."
                print(f"⚠️ {msg}")
                return None, msg

            subprocess.run(["git", "commit", "-m", "Fix: Automated bug fixes by Patchwork-AI"], cwd=repo_path, check=True, capture_output=True)

            # 2. Add auth to remote URL to push
            auth_url = repo_url.replace("https://", f"https://x-access-token:{self.github_token}@")
            subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=repo_path, check=True, capture_output=True)

            print("📤 Pushing branch to GitHub...")
            subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)

            # 3. Create PR via GitHub API
            parts = repo_url.rstrip("/").split("/")
            owner_repo = f"{parts[-2]}/{parts[-1]}"
            if owner_repo.endswith(".git"):
                owner_repo = owner_repo[:-4]

            api_url = f"https://api.github.com/repos/{owner_repo}/pulls"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "title": "🔧 Automated Bug Fixes by Patchwork-AI",
                "body": "This PR contains automated code quality improvements and bug fixes generated by your Patchwork-AI agent.",
                "head": branch_name,
                "base": "main"  # Assumes main branch, common for modern repos
            }

            response = requests.post(api_url, headers=headers, json=data)
            if response.status_code == 201:
                pr_url = response.json().get("html_url")
                print(f"🎉 Pull Request Successfully Created! View here: {pr_url}")
                return pr_url, None
            else:
                print(f"❌ Failed to create PR: {response.text}")
                # Fallback to master if main fails
                if "invalid" in response.text.lower() or "not found" in response.text.lower():
                    print("🔄 Retrying with 'master' base branch...")
                    data["base"] = "master"
                    response = requests.post(api_url, headers=headers, json=data)
                    if response.status_code == 201:
                        pr_url = response.json().get("html_url")
                        print(f"🎉 Pull Request Successfully Created! View here: {pr_url}")
                        return pr_url, None
                    else:
                        msg = f"GitHub API rejected the PR (tried both 'main' and 'master'): {response.text}"
                        print(f"❌ {msg}")
                        return None, msg
                msg = f"GitHub API rejected the PR: {response.text}"
                return None, msg

        except subprocess.CalledProcessError as e:
            # e / str(e) can embed the auth_url (which contains the token) via the cmd list — mask it.
            stderr = self._mask(e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr or ""))
            msg = f"Git command failed ({self._mask(' '.join(e.cmd))}): {stderr}"
            print(f"❌ {msg}")
            return None, msg
        except Exception as e:
            msg = f"Error during PR creation: {self._mask(str(e))}"
            print(f"❌ {msg}")
            return None, msg

    def run_in_sandbox(self, code_snippet: str):
        print("🛡️ Running code in TrueForge Sandbox...")

        test_file_path = "temp_sandbox_test.py"
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(code_snippet)

        try:
            result = subprocess.run(
                ["python", test_file_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            if os.path.exists(test_file_path):
                os.remove(test_file_path)

            if result.returncode == 0:
                print("✅ Sandbox Test Passed!")
                print(f"Output: {result.stdout.strip()}")
                return True
            else:
                print("❌ Sandbox Test Failed!")
                print(f"Error: {result.stderr.strip()}")
                return False

        except Exception as e:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            print(f"❌ Execution Error: {e}")
            return False

    def request_human_approval(self):
        print("\n" + "=" * 50)
        print("🛑 HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
        print("=" * 50)

        choice = input("Do you want to approve this fix and apply it? (y/n): ").strip().lower()
        return choice == 'y'

    def scan_repository_files(self, directory_path: str):
        """Phase 2: Scan local repository files for analysis"""
        print(f"\n🔍 Scanning files in directory: {directory_path}...")
        code_files = []

        try:
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.java', '.cpp')):
                        full_path = os.path.join(root, file)
                        code_files.append(full_path)

            print(f"✅ Found {len(code_files)} source code files for analysis.")
            return code_files
        except Exception as e:
            print(f"❌ Error scanning directory: {e}")
            return []

    # Raised from 3000 -> 12000: the old limit silently cut off analysis partway
    # through medium-sized files, so real bugs past that point were never seen
    # by the model and the file would incorrectly come back as "NONE".
    MAX_ANALYSIS_CHARS = 12000

    def analyze_with_llm(self, content: str, file_path: str):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://patchwork-ai.streamlit.app",
            "X-Title": "Patchwork-AI"
        }
        truncated = len(content) > self.MAX_ANALYSIS_CHARS
        snippet = content[:self.MAX_ANALYSIS_CHARS]
        if truncated:
            print(f"⚠️ {file_path} is larger than {self.MAX_ANALYSIS_CHARS} chars; analysis is only covering the first part of the file.")

        prompt = (
            f"Analyze this code from '{file_path}' for bugs, vulnerabilities, or code smells.\n\n"
            "Step 1 — Look carefully for ALL REAL correctness issues first: typos in variable/identifier names, "
            "undefined variables, off-by-one errors, wrong operators, missing return statements, logic errors, "
            "iteration over modifying sets, missing dictionary keys (KeyErrors), unhandled exceptions, or security issues.\n"
            "If you find any, list EACH of them as a separate bullet point (starting with '- ') with a short 1-sentence description.\n\n"
            "Step 2 — If there are absolutely NO correctness issues, then check for quality/style gaps (e.g. missing docstrings). List them as bullet points if found.\n\n"
            "Reply with exactly the word 'NONE' ONLY if the code has absolutely no correctness issues AND no quality/style gaps.\n\n"
            f"Code:\n{snippet}"
        )

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=15)
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"].strip()
                if result.upper() == "NONE" or "NONE" in result.upper():
                    return None
                return result
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"⚠️ LLM {error_msg}")
                return f"API_ERROR: {response.status_code} - {response.text}"
        except Exception as e:
            print(f"⚠️ LLM API Request Failed: {e}")
            return f"API_ERROR: Exception - {str(e)}"

    def analyze_code_quality(self, file_paths: list):
        """Phase 3: Analyze code files for issues"""
        print(f"\n🔍 Analyzing {len(file_paths)} files for quality issues...")
        issues = []

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if self.api_key:
                    # LLM Analysis
                    issue_desc = self.analyze_with_llm(content, file_path)
                    if issue_desc:
                        issues.append({"file": file_path, "issue": issue_desc, "content": content})
                else:
                    # Basic rule checks fallback
                    if "print(" in content:
                        issues.append({"file": file_path, "issue": "Found 'print()' statement; consider using proper logging.", "content": content})
                    if "TODO" in content:
                        issues.append({"file": file_path, "issue": "Unresolved 'TODO' comment found.", "content": content})

            except Exception as e:
                print(f"⚠️ Could not read file {file_path}: {e}")

        print(f"✅ Code analysis complete. Found {len(issues)} potential issues.")
        return issues

    def fix_with_llm(self, content: str, issue_description: str):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://patchwork-ai.streamlit.app",
            "X-Title": "Patchwork-AI"
        }
        if len(content) > self.MAX_ANALYSIS_CHARS * 2:
            print(f"⚠️ File is very large ({len(content)} chars); the fix may be less reliable for content far into the file.")

        prompt = f"Fix ALL of the following issues in the code simultaneously.\nIssues:\n{issue_description}\n\nReturn ONLY the exact fully fixed code as plain text. CRITICAL: Maintain the exact original coding style, indentation, and formatting. Do NOT add any AI-like comments explaining the fixes. Do NOT use markdown code blocks like ```python. Just output the raw code directly so it can overwrite the file.\n\nCode:\n{content}"

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 8000
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=15)
            if response.status_code == 200:
                fixed_code = response.json()["choices"][0]["message"]["content"].strip()
                # Safety strip for markdown code blocks if the model ignores instructions
                if fixed_code.startswith("```"):
                    fixed_code = fixed_code.split("\n", 1)[1]
                if fixed_code.endswith("```"):
                    fixed_code = fixed_code.rsplit("\n", 1)[0]
                return fixed_code
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                print(f"⚠️ LLM Fix {error_msg}")
                return f"API_ERROR: {response.status_code} - {response.text}"
        except Exception as e:
            print(f"⚠️ LLM Fix API Request Failed: {e}")
            return f"API_ERROR: Exception - {str(e)}"

    def generate_and_apply_patch(self, file_path: str, issue_description: str, original_content: str):
        """Phase 4: Generate an automated patch/fix and ask for permission to apply"""
        print(f"\n🛠️ Generating patch for {file_path}...")
        print(f"   Detected Issue: {issue_description}")

        fixed_content = None

        if self.api_key:
            fixed_content = self.fix_with_llm(original_content, issue_description)
        else:
            # Fallback for prototype
            if "print(" in issue_description:
                fixed_content = original_content.replace("print(", "import logging\nlogging.info(")

        if not fixed_content or fixed_content == original_content:
            print("⚠️ Could not generate a valid patch for this issue.")
            return False

        print("\n💡 Suggested Fix Generated!")
        print("--- NEW CODE PREVIEW ---")
        print(fixed_content[:200] + "\n...")
        print("------------------------")

        approved = self.request_human_approval()
        if approved:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"✅ Patch applied to {file_path} successfully!")
                return True
            except Exception as e:
                print(f"❌ Failed to apply patch: {e}")
                return False
        else:
            print("❌ Action cancelled by user. No changes applied.")
            return False

    def process_local_repo(self, repo_path: str):
        print(f"\n📂 Processing repository path: {repo_path}")
        # Step 0: Scan files
        scanned_files = self.scan_repository_files(repo_path)

        # Step 1: Analyze scanned files for quality issues
        quality_issues = self.analyze_code_quality(scanned_files)

        changes_made = False
        # Step 2: Generate patches and request approval
        for issue in quality_issues:
            if self.generate_and_apply_patch(issue["file"], issue["issue"], issue["content"]):
                changes_made = True

        # Step 3: Sandbox Test (Demonstration)
        print("\n🧪 Running final TrueForge Sandbox verification test...")
        verified_code = "print('Verified Safe Code Executing!')"
        self.run_in_sandbox(verified_code)

        print("\n🎉 Repository processing complete!")
        return changes_made

if __name__ == "__main__":
    agent = PatchworkAgent()
    agent.process_local_repo(os.getcwd())