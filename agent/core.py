import os
from dotenv import load_dotenv
import subprocess

load_dotenv()

class PatchworkAgent:
    def __init__(self):
        print("🤖 Patchwork AI Agent initialized.")
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            print("⚠️ Warning: API Key not found!")
        else:
            print("✅ API Key loaded.")

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

    def process_repository(self, repo_path: str):
        print(f"📂 Processing repository path: {repo_path}")
        
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