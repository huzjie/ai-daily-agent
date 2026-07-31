#!/usr/bin/env python3
"""
AI Daily Agent - 自动配置脚本
只需运行一次，自动完成所有配置
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("🐍 检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ 需要 Python 3.8+，当前是 {version.major}.{version.minor}")
        return False


def check_dependencies():
    """检查并安装依赖"""
    print("\n📦 检查依赖...")
    try:
        import yaml
        import requests
        from bs4 import BeautifulSoup
        print("✅ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"⚠️  缺少依赖: {e}")
        print("正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        return True


def check_git():
    """检查 Git"""
    print("\n🔧 检查 Git...")
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("❌ Git 未安装")
        return False


def check_gh_cli():
    """检查 GitHub CLI"""
    print("\n🐙 检查 GitHub CLI...")
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        print("⚠️  GitHub CLI 未安装")
        print("\n请安装 GitHub CLI:")
        print("  Windows: winget install --id GitHub.cli")
        print("  或访问: https://cli.github.com/")
        return False


def check_gh_auth():
    """检查 GitHub 认证"""
    print("\n🔐 检查 GitHub 认证...")
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GitHub 已认证")
            return True
        else:
            print("⚠️  GitHub 未认证")
            return False
    except FileNotFoundError:
        print("❌ gh CLI 不可用")
        return False


def get_github_username():
    """获取 GitHub 用户名"""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def auto_login_github():
    """自动登录 GitHub"""
    print("\n🔐 登录 GitHub...")
    print("请在浏览器中完成授权...\n")
    
    try:
        result = subprocess.run(
            ["gh", "auth", "login", "--web", "--git-protocol", "https"],
            input="n\n",  # 不设置 git 作为默认编辑器
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ GitHub 登录成功")
            return True
        else:
            print("❌ GitHub 登录失败")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def create_env_file(username: str, token: str):
    """创建 .env 文件"""
    print("\n📝 创建 .env 文件...")
    env_content = f"""# AI Daily Agent - 环境变量配置
# 自动生成于 {__import__('datetime').datetime.now().isoformat()}

# GitHub Configuration
GITHUB_USERNAME={username}
GITHUB_TOKEN={token}

# 可选：OpenAI API（用于增强项目生成）
# OPENAI_API_KEY=your_openai_api_key
"""
    
    env_file = Path(".env")
    env_file.write_text(env_content, encoding='utf-8')
    print("✅ .env 文件已创建")


def update_config(username: str):
    """更新 config.yaml"""
    print("\n⚙️  更新配置文件...")
    import yaml
    
    config_file = Path("config.yaml")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    config['github']['username'] = username
    
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print("✅ config.yaml 已更新")


def create_data_directories():
    """创建数据目录"""
    print("\n📁 创建数据目录...")
    dirs = [
        "data/projects",
        "data/logs",
        "data/metrics",
        "data/reports",
    ]
    
    for dir_path in dirs:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    
    print("✅ 数据目录已创建")


def test_agent():
    """测试 Agent"""
    print("\n🧪 测试 AI Daily Agent...")
    
    try:
        from agent import AIDailyAgent
        agent = AIDailyAgent('config.yaml')
        
        # 测试配置加载
        print("✅ 配置加载成功")
        
        # 测试模块初始化
        print("✅ 模块初始化成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI Daily Agent - 自动配置向导")
    print("=" * 60)
    
    # 检查基础环境
    if not check_python_version():
        return False
    
    if not check_dependencies():
        return False
    
    if not check_git():
        return False
    
    # 检查 GitHub CLI
    if not check_gh_cli():
        print("\n⚠️  请先安装 GitHub CLI，然后重新运行此脚本")
        return False
    
    # 检查 GitHub 认证
    if not check_gh_auth():
        print("\n需要进行 GitHub 认证")
        print("即将打开浏览器进行授权...")
        input("\n按 Enter 继续...")
        
        if not auto_login_github():
            print("\n❌ GitHub 认证失败")
            return False
    
    # 获取 GitHub 用户名
    username = get_github_username()
    if not username:
        print("\n❌ 无法获取 GitHub 用户名")
        return False
    
    print(f"\n✅ GitHub 用户: {username}")
    
    # 获取 Token
    print("\n🔑 需要创建 GitHub Personal Access Token")
    print("\n请按以下步骤操作:")
    print("1. 访问: https://github.com/settings/tokens")
    print("2. 点击 'Generate new token (classic)'")
    print("3. 勾选 'repo' 权限")
    print("4. 生成并复制 Token")
    print("\n或者运行以下命令自动创建:")
    print("  gh auth token")
    
    token = input("\n请粘贴你的 GitHub Token: ").strip()
    if not token:
        print("\n❌ Token 不能为空")
        return False
    
    # 创建配置文件
    create_env_file(username, token)
    update_config(username)
    
    # 创建数据目录
    create_data_directories()
    
    # 测试 Agent
    if not test_agent():
        print("\n⚠️  Agent 测试失败，但配置已完成")
        return False
    
    # 完成
    print("\n" + "=" * 60)
    print("🎉 配置完成！")
    print("=" * 60)
    print("\n✅ 所有配置已就绪")
    print("✅ 系统已准备就绪")
    print("\n现在你可以:")
    print("  1. 手动运行: python agent.py")
    print("  2. 等待自动化任务（每天早上 9:00 自动运行）")
    print("\n祝你建立强大的技术品牌！🚀")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
