import os
from typing import List

class CodebaseAdvisoryService:
    def __init__(self, root_dir: str = "/data/data/com.termux/files/home/Monu"):
        self.root_dir = os.path.abspath(root_dir)

    def scan_codebase(self) -> str:
        """Scans the codebase and returns a formatted string of source files."""
        allowed_extensions = {'.py', '.dart', '.yaml', '.txt', '.sh', '.json', '.md'}
        ignored_dirs = {
            '.git', '.github', '.gradle', '.idea', 'build', 'ios', 'android', 
            'linux', 'macos', 'windows', 'web', '__pycache__', 'node_modules', 
            'user_data', '.dart_tool'
        }
        ignored_files = {
            'package-lock.json', 'assistant.db', 'release.jks', 
            'upload-keystore.jks', 'assistant.db-journal', 'pubspec.lock'
        }
        
        context_parts = []
        
        for root, dirs, files in os.walk(self.root_dir):
            # Modify dirs in-place to ignore specified directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file in files:
                if file in ignored_files:
                    continue
                
                ext = os.path.splitext(file)[1]
                if ext in allowed_extensions:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    
                    try:
                        # Limit reading file sizes to prevent massive memory usage
                        if os.path.getsize(full_path) < 100 * 1024:  # < 100KB
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            context_parts.append(f"=== File: {rel_path} ===\n{content}\n")
                    except Exception as e:
                        print(f"Error reading {rel_path}: {e}")
                        
        return "\n".join(context_parts)

codebase_advisory_service = CodebaseAdvisoryService()
