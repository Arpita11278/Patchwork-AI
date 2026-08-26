import os
from agent.core import PatchworkAgent

def main():
    print("🚀 Initializing Patchwork-AI Autonomous Agent...")
    
    # Initialize the agent (aap yahan apna GitHub token ya repo path de sakte hain)
    agent = PatchworkAgent()
    
    # Current repository path (apna current project folder)
    repo_path = os.getcwd()
    
    # Run the full automated pipeline
    agent.process_repository(repo_path)
    
    print("\n✨ Patchwork-AI Workflow Completed Successfully!")

if __name__ == "__main__":
    main()