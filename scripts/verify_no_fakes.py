#!/usr/bin/env python3
"""
Anti-fabrication check (Gate 10).
Fails the build if any of the anti-fabrication rules are violated.
"""
import os
import sys
import re

def check_file(filepath):
    errors = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Rule 1: Literal PASS/FAIL assigned outside verification engine
                if 'verification' not in filepath and 'tests' not in filepath:
                    if re.search(r'status\s*=\s*["\'](PASS|FAIL)["\']', line, re.IGNORECASE):
                        errors.append(f"{filepath}:{line_num} Rule 12.1 violation: Literal PASS/FAIL assignment outside verification engine.")
                        
                # Rule 2: Hardcoded numeric metric in reporting
                if 'reporting' in filepath:
                    if re.search(r'(score|coverage)\s*=\s*[0-9]+', line, re.IGNORECASE):
                        errors.append(f"{filepath}:{line_num} Rule 12.1 violation: Hardcoded numeric metric in reporting module.")
                        
                # Rule 3: Import of a mock/stub under src/
                if 'tests' not in filepath:
                    if re.search(r'import.*(mock|fake|stub)', line, re.IGNORECASE):
                        errors.append(f"{filepath}:{line_num} Rule 12.1 violation: Import of a mock/fake/stub in source module.")
                        
                # Rule 4: shell=True usage
                if 'shell=True' in line:
                    errors.append(f"{filepath}:{line_num} Rule 12.1 violation: Use of shell=True is prohibited.")
                    
                # Rule 5: Swallowed exception
                # This is harder to grep reliably, but we can check for empty except blocks
                if 'except ' in line and i+1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line == 'pass':
                        errors.append(f"{filepath}:{line_num+1} Rule 12.1 violation: Swallowed exception (except block with just 'pass').")

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return errors

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ps3_dir = os.path.join(root_dir, 'ps3')
    
    all_errors = []
    for dirpath, _, filenames in os.walk(ps3_dir):
        if '__pycache__' in dirpath:
            continue
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                errors = check_file(filepath)
                all_errors.extend(errors)
                
    if all_errors:
        print("ANTI-FABRICATION CHECK FAILED:")
        for error in all_errors:
            print(error)
        sys.exit(1)
    else:
        print("ANTI-FABRICATION CHECK PASSED.")
        sys.exit(0)

if __name__ == '__main__':
    main()
