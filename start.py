#!/usr/bin/env python3
"""
AI Daily Agent - 一键启动脚本
真正的全自动模式：零手动操作
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def log(msg):
    """输出带时间戳的日志"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def run(cmd, input_text=None):
    """执行命令并返回 (success, output)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=120
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_python():
    """检查 Python"""
    if sys.version_info < (3, 8):
        log("❌ 需要 Python 3.8+")
        return False
    log(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """检查并安装依赖"""
    try:
        import yaml
        import requests
        from bs4 import BeautifulSoup
        log("✅ 依赖已就绪")
        return True
    except ImportError:
        log("⚠️  正在安装依赖...")
        ok, out, err = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        if ok:
            log("✅ 依赖安装完成")
        else:
            log(f"❌ 依赖安装失败: {err}")
        return ok


def check_git():
    """检查 Git"""
    ok, out, _ = run(["git", "--version"])
    if ok:
        log(f"✅ Git: {out}")
        return True
    log("❌ Git 未安装")
    return False


def check_gh_cli():
    """检查并自动安装 GitHub CLI"""
    ok, out, _ = run(["gh", "--version"])
    if ok:
        log(f"✅ GitHub CLI: {out.splitlines()[0] if out else 'installed'}")
        return True
    
    log("⚠️  GitHub CLI 未安装，正在自动安装...")
    ok, out, err = run(["winget", "install", "--id", "GitHub.cli", "--accept-package-agreements", "--accept-source-agreements"])
    if ok:
        log("✅ GitHub CLI 安装完成")
        # 刷新 PATH
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + r"C:\Program Files\GitHub CLI"
        ok2, _, _ = run(["gh", "--version"])
        return ok2
    else:
        log(f"❌ 自动安装失败: {err}")
        return False


def auto_login_github():
    """自动登录 GitHub"""
    ok, _, _ = run(["gh", "auth", "status"])
    if ok:
        log("✅ GitHub 已认证")
        return True
    
    log("⚠️  GitHub 未认证，正在自动登录...")
    log("📱 请在弹出的浏览器窗口中完成授权")
    
    # 使用 device code flow，会自动打开浏览器
    ok, out, err = run(
        ["gh", "auth", "login", "--hostname", "github.com", "--web", "--git-protocol", "https"],
        input_text="\n"
    )
    
    if ok or "already" in (out + err).lower():
        log("✅ GitHub 登录成功")
        return True
    
    log(f"❌ GitHub 登录失败: {err}")
    return False


def get_github_username():
    """获取 GitHub 用户名"""
    ok, out, _ = run(["gh", "api", "user", "--jq", ".login"])
    if ok and out:
        log(f"✅ GitHub 用户: {out}")
        return out
    return None


def get_github_token():
    """获取 GitHub Token"""
    ok, out, _ = run(["gh", "auth", "token"])
    if ok and out:
        log("✅ Token 已获取")
        return out
    return None


def auto_configure(username, token):
    """自动配置所有文件"""
    log("⚙️  正在自动配置...")
    
    # 创建 .env
    env_content = f"""# AI Daily Agent - 自动配置
# 配置时间: {datetime.now().isoformat()}

GITHUB_USERNAME={username}
GITHUB_TOKEN={token}
"""
    Path(".env").write_text(env_content, encoding='utf-8')
    log("✅ .env 已创建")
    
    # 更新 config.yaml
    import yaml
    config_file = Path("config.yaml")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        config['github']['username'] = username
        config['github']['token'] = token
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        log("✅ config.yaml 已更新")
    
    # 创建数据目录
    for dir_path in ["data/projects", "data/logs", "data/metrics", "data/reports"]:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
    log("✅ 数据目录已创建")
    
    # 标记已配置
    Path(".configured").write_text(datetime.now().isoformat(), encoding='utf-8')
    log("✅ 配置完成")


def run_agent():
    """运行 Agent"""
    log("=" * 60)
    log(f"🚀 AI Daily Agent - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log("=" * 60)
    
    try:
        # 添加当前目录到 sys.path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from agent import AIDailyAgent
        
        agent = AIDailyAgent('config.yaml')
        result = agent.run_daily_pipeline()
        
        if result['status'] == 'success':
            log("=" * 60)
            log("✅ 今日任务完成！")
            log("=" * 60)
            
            if 'publish' in result['steps'] and result['steps']['publish'].get('status') == 'success':
                repo_url = result['steps']['publish'].get('repo_url', '')
                if repo_url:
                    log(f"📦 项目已发布: {repo_url}")
            
            log("📊 系统将按计划自动继续运行")
            return True
        else:
            log(f"❌ 任务执行失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        log(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数 - 全自动"""
    print()
    log("=" * 60)
    log("🤖 AI Daily Agent - 全自动模式")
    log("=" * 60)
    print()
    
    # Step 1: 环境检查
    log("📋 Step 1/4: 检查环境")
    if not check_python():
        return False
    
    if not check_dependencies():
        return False
    
    if not check_git():
        return False
    
    if not check_gh_cli():
        return False
    
    print()
    
    # Step 2: GitHub 认证
    log("📋 Step 2/4: GitHub 认证")
    if not auto_login_github():
        return False
    
    username = get_github_username()
    if not username:
        log("❌ 无法获取 GitHub 用户名")
        return False
    
    token = get_github_token()
    if not token:
        log("❌ 无法获取 GitHub Token")
        return False
    
    print()
    
    # Step 3: 自动配置
    log("📋 Step 3/4: 自动配置")
    auto_configure(username, token)
    
    print()
    
    # Step 4: 运行 Agent
    log("📋 Step 4/4: 运行 Agent")
    success = run_agent()
    
    print()
    if success:
        log("🎉 全部完成！明天见！")
    else:
        log("⚠️  运行失败，请查看日志: data/logs/agent.log")
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        log("⚠️  已取消")
        sys.exit(1)
    except Exception as e:
        log(f"❌ 严重错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
