import os
import shutil
from pathlib import Path

def main():
    root_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Clear README.md
    readme_path = root_dir / "README.md"
    if readme_path.exists():
        readme_path.write_text("# NDLM Bharat Pashudhan - AI Breed Recognition Platform\n\nPrototype for Smart India Hackathon 2025.\n", encoding="utf-8")
        print("Cleared README.md")

    # 2. Create archive directory
    archive_dir = root_dir / "ml_pipeline_archive"
    archive_dir.mkdir(exist_ok=True)
    
    # 3. Move scripts and reports
    keep_files = {
        ".gitignore", "README.md", "requirements.txt", 
        "run_dashboard.bat", "run_dashboard.sh", "organize_project.py",
        "conftest.py"
    }
    
    for item in root_dir.iterdir():
        if item.is_file() and item.name not in keep_files and item.name != ".git":
            if item.name.endswith(".py") or item.name.endswith(".md") or item.name.endswith(".json") or item.name.endswith(".png") or item.name.endswith(".jpg") or item.name.endswith(".bat"):
                # Move to archive
                dest = archive_dir / item.name
                shutil.move(str(item), str(dest))
                print(f"Moved {item.name} to archive")
                
if __name__ == '__main__':
    main()
