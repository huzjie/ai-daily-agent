# Setup Script for AI Daily Agent
# Run this script to verify everything is configured correctly

import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8 or higher is required")
        return False
    return True

def check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import yaml
        import requests
        from bs4 import BeautifulSoup
        print("✓ All dependencies installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        return False

def check_config():
    """Check if config.yaml exists"""
    if Path('config.yaml').exists():
        print("✓ config.yaml found")
        return True
    else:
        print("✗ config.yaml not found")
        return False

def check_env():
    """Check if .env file exists"""
    if Path('.env').exists():
        print("✓ .env file found")
        
        # Load and check env variables
        with open('.env', 'r') as f:
            env_content = f.read()
            
        if 'GITHUB_USERNAME=your_github_username' in env_content:
            print("⚠ GitHub username not configured yet")
            print("  → Edit .env and set your GitHub username")
            return False
        
        if 'GITHUB_TOKEN=your_github_personal_access_token' in env_content:
            print("⚠ GitHub token not configured yet")
            print("  → Edit .env and set your GitHub token")
            return False
        
        print("✓ GitHub configuration looks good")
        return True
    else:
        print("✗ .env file not found")
        print("  → Run: cp .env.example .env")
        return False

def check_gh_cli():
    """Check if GitHub CLI is installed"""
    import subprocess
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ GitHub CLI installed: {result.stdout.split()[2]}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("✗ GitHub CLI (gh) not found")
    print("  → Install from: https://cli.github.com/")
    return False

def check_directories():
    """Check if all required directories exist"""
    required_dirs = [
        'data/projects',
        'data/logs',
        'data/metrics',
        'data/reports'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/ exists")
        else:
            print(f"✗ {dir_path}/ missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all checks"""
    print("=" * 60)
    print("AI Daily Agent - Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Configuration", check_config),
        ("Environment", check_env),
        ("GitHub CLI", check_gh_cli),
        ("Directories", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Total: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! You're ready to run the agent.")
        print("\nNext steps:")
        print("1. Test with: python agent.py --config config.yaml")
        print("2. Or try with a custom topic: python agent.py --topic 'Your AI Topic'")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick start guide:")
        print("1. Install GitHub CLI: https://cli.github.com/")
        print("2. Login: gh auth login")
        print("3. Copy .env.example to .env: cp .env.example .env")
        print("4. Edit .env with your GitHub credentials")
        print("5. Run this setup check again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
