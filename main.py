import os
from agent.core import PatchworkAgent

def main():
    print("🚀 Initializing Patchwork-AI Autonomous Agent...")
    
    agent = PatchworkAgent()
    
    print("\nDo you want to process a GitHub URL or a local folder?")
    print("1. GitHub URL")
    print("2. Local Folder (current directory)")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == '1':
        repo_url = input("Enter GitHub repository URL (e.g., https://github.com/user/repo): ").strip()
        agent.process_github_repo(repo_url)
    else:
        repo_path = os.getcwd()
        agent.process_local_repo(repo_path)
    
    print("\n✨ Patchwork-AI Workflow Completed Successfully!")

if __name__ == "__main__":
    main()