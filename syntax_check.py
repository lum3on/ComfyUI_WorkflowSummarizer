#!/usr/bin/env python3
"""
Syntax check for the enhanced ComfyUI Workflow Summarizer
"""

import ast
import sys
import os

def check_syntax(filename):
    """Check if a Python file has valid syntax"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(source, filename=filename)
        print(f"✅ {filename}: Syntax OK")
        return True
        
    except SyntaxError as e:
        print(f"❌ {filename}: Syntax Error at line {e.lineno}: {e.msg}")
        print(f"   {e.text.strip() if e.text else ''}")
        return False
    except Exception as e:
        print(f"❌ {filename}: Error reading file: {e}")
        return False

def main():
    """Check syntax of all Python files"""
    files_to_check = [
        "scanner.py",
        "workflow_summary.py", 
        "test_enhanced_features.py",
        "mock_folder_paths.py"
    ]
    
    print("🔍 Checking Python syntax...")
    print("=" * 40)
    
    all_good = True
    for filename in files_to_check:
        if os.path.exists(filename):
            if not check_syntax(filename):
                all_good = False
        else:
            print(f"⚠️  {filename}: File not found")
            all_good = False
    
    print("=" * 40)
    if all_good:
        print("🎉 All files have valid syntax!")
    else:
        print("❌ Some files have syntax errors.")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
