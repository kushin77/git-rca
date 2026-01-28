import os
import sys

def scan_project(root_dir="."):
    print(f"🔍 Scanning project for cleanup opportunities in: {os.path.abspath(root_dir)}")
    
    issues_found = []
    
    # 1. Check for large files (> 1MB)
    print("\n📦 Checking for large files...")
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or "node_modules" in root or "venv" in root or ".venv" in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            if os.path.islink(path): continue
            size = os.path.getsize(path)
            if size > 1024 * 1024:
                issues_found.append(f"LARGE FILE: {path} ({size / 1024 / 1024:.2f} MB)")
                print(f"  [!] {path} is large")

    # 2. Check for TODOs/FIXMEs
    print("\n📝 Checking for TODOs and FIXMEs...")
    extensions = ('.py', '.md', '.txt', '.sh', '.yaml', '.yml', '.json')
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or "venv" in root or ".venv" in root:
            continue
        for file in files:
            if file.endswith(extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if "TODO" in line or "FIXME" in line:
                                issues_found.append(f"DEBT: {path}:{i} - {line.strip()}")
                except:
                    pass

    # 3. Check for potential duplicates
    print("\n👯 Checking for potential duplicate filenames...")
    file_map = {}
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or "venv" in root or ".venv" in root:
            continue
        for file in files:
            if file not in file_map:
                file_map[file] = []
            file_map[file].append(os.path.join(root, file))
    
    for file, paths in file_map.items():
        if len(paths) > 1 and not file.endswith(('.pyc', '__init__.py', 'README.md')):
            issues_found.append(f"DUPLICATE? {file} found in {len(paths)} locations: {paths}")
            print(f"  [!] Found multiple instances of {file}")

    # 4. Check for empty files
    print("\n🕳️ Checking for empty files...")
    for root, dirs, files in os.walk(root_dir):
        if ".git" in root or "venv" in root or ".venv" in root:
            continue
        for file in files:
            path = os.path.join(root, file)
            if os.path.getsize(path) == 0:
                issues_found.append(f"EMPTY FILE: {path}")

    # Summary
    print("\n" + "="*50)
    print(f"📊 SUMMARY: Found {len(issues_found)} potential cleanup items.")
    print("="*50)
    for issue in issues_found:
        print(issue)

if __name__ == "__main__":
    scan_project()
