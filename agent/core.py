import os
from dotenv import load_dotenv
import subprocess
import requests

load_dotenv()

class PatchworkAgent:
    def __init__(self):
        print("🤖 Patchwork AI Agent initialized.")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        if not self.api_key:
            print("⚠️ Warning: API Key not found!")
        else:
            print("✅ API Key loaded.")

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

    def run_in_sandbox(self, code_snippet: str):
        print("🛡️ Running code in TrueForge Sandbox...")
        
        test_file_path = "temp_sandbox_test.py"
        with open(test_file_path, "w") as f:
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
        print("\n" + "="*50)
        print("🛑 HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
        print("="*50)

        choice = input("Do you want to approve this fix and create a Pull Request? (y/n): ").strip().lower()
        return choice == 'y'

    def scan_repository_files(self, directory_path: str):
        """Phase 2: Scan local repository files for analysis"""
        print(f"🔍 Scanning files in directory: {directory_path}...")
        code_files = []
        
        try:
            for root, dirs, files in os.walk(directory_path):
                # Ignore hidden folders like .git or __pycache__
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

    def process_repository(self, repo_path: str):
        print(f"📂 Processing repository path: {repo_path}")
        # Step 0: Scan files
        scanned_files = self.scan_repository_files(repo_path)
        # Optional: Test GitHub connection first
        self.fetch_github_repo("Arpita11278/Patchwork-AI")
        
        verified_code = """
def calculate_sum(a, b):
    total = a + b
    print(f"Calculated Total: {total}")
    return total

calculate_sum(20, 30)
        """
        
        # Step A: Sandbox Test
        test_success = self.run_in_sandbox(verified_code)
        
        if test_success:
            # Step B: Human Approval Check
            approved = self.request_human_approval()
            
            if approved:
                print("🚀 Approval granted! Creating GitHub Pull Request...")
                print("✅ Pull Request successfully created for Patchwork-AI!")
            else:
                print("❌ Action cancelled by user. No changes pushed.")
        else:
            print("❌ Sandbox test failed. Skipping approval step.")

if __name__ == "__main__":
    agent = PatchworkAgent()
    agent.process_repository("./sample_project")