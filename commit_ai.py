#!/usr/bin/env python3
import sys
import subprocess
import urllib.request
import urllib.error
import json
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:1.5b"
MAX_DIFF_LENGTH = 2000

def get_git_diff():
    try:
        result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return ""

def main():
    if len(sys.argv) < 2:
        sys.exit(0)
    
    commit_msg_file = sys.argv[1]
    
    if not os.path.exists(commit_msg_file):
        sys.exit(0)
        
    diff = get_git_diff()
    if not diff.strip():
        sys.exit(0)
        
    if len(diff) > MAX_DIFF_LENGTH:
        diff = diff[:MAX_DIFF_LENGTH] + "\n...[diff truncated]"
        
    prompt = f"""Write a git commit message following the Conventional Commits specification based on the git diff provided below.
Rules:
- Format: <type>(<optional scope>): <description>
- Include a blank line and then a more detailed body if necessary.
- Do not wrap the message in code blocks or quotes.
- Only output the commit message, no introductions or explanations.

Git Diff:
{diff}
"""

    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    req = urllib.request.Request(
        OLLAMA_URL, 
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                commit_msg = response_data.get('response', '').strip()
                
                if commit_msg:
                    with open(commit_msg_file, 'r') as f:
                        original_content = f.read()
                        
                    with open(commit_msg_file, 'w') as f:
                        f.write(f"{commit_msg}\n\n{original_content}")
                        
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, Exception):
        # Fallback to manual commit message on failure
        sys.exit(0)

if __name__ == "__main__":
    main()
