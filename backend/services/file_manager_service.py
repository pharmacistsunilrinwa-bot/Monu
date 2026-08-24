import os
import shutil
from typing import List

class FileManagerService:
    def __init__(self, base_dir: str = "user_data"):
        self.base_dir = os.path.abspath(base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _secure_path(self, relative_path: str) -> str:
        # Generate the absolute path of the target
        target_path = os.path.abspath(os.path.join(self.base_dir, relative_path))
        
        # Verify that the path does not escape base_dir using commonpath
        if os.path.commonpath([self.base_dir, target_path]) != self.base_dir:
            raise PermissionError("Access denied: Target path is outside of user directory.")
        return target_path

    def list_files(self, sub_dir: str = "") -> List[str]:
        target_dir = self._secure_path(sub_dir)
        if not os.path.isdir(target_dir):
            raise FileNotFoundError(f"Directory {sub_dir} not found.")
        return os.listdir(target_dir)

    def create_directory(self, dir_name: str):
        target_dir = self._secure_path(dir_name)
        os.makedirs(target_dir, exist_ok=True)
        return f"Directory {dir_name} created."

    def delete_file(self, file_name: str):
        target_path = self._secure_path(file_name)
        if os.path.isfile(target_path):
            os.remove(target_path)
            return f"File {file_name} deleted."
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
            return f"Directory {file_name} deleted."
        return "File not found."

    def move_file(self, src: str, dst: str):
        target_src = self._secure_path(src)
        target_dst = self._secure_path(dst)
        
        if not os.path.exists(target_src):
            raise FileNotFoundError(f"Source path {src} not found.")
            
        shutil.move(target_src, target_dst)
        return f"Moved {src} to {dst}."

file_manager_service = FileManagerService()
