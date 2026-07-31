# Quick Start Guide - AI Daily Agent

## 🚀 5 分钟快速启动

### Step 1: 安装 GitHub CLI

```bash
# Windows (使用 winget)
winget install --id GitHub.cli

# 或者下载安装包
# https://cli.github.com/
```

### Step 2: 登录 GitHub

```bash
gh auth login
```

按照提示选择：
- GitHub.com
- HTTPS
- Login with a web browser
- 复制代码并在浏览器中完成授权

### Step 3: 配置环境变量

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
# Windows: notepad .env
# Mac/Linux: nano .env
```

填写以下信息：
```
GITHUB_USERNAME=你的GitHub用户名
GITHUB_TOKEN=你的Personal Access Token
```

**获取 Token：**
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 生成并复制 token

### Step 4: 验证配置

```bash
python setup_check.py
```

如果所有检查都通过，就可以开始使用了！

### Step 5: 运行 Agent

```bash
# 完整流程（发现热点 + 生成项目 + 发布）
python agent.py --config config.yaml

# 或者指定自定义主题
python agent.py --topic "Multi-Agent Collaboration Framework"

# 仅监控模式（更新指标）
python agent.py --monitor-only
```

## 📋 日常使用

### 手动运行

```bash
# 每天早上运行一次
python agent.py
```

### 查看结果

- 生成的项目在 `data/projects/` 目录
- 运行日志在 `data/logs/agent.log`
- 监控报告在 `data/reports/`

### 查看 GitHub 仓库

```bash
# 查看所有已发布的仓库
cat data/published_repos.json

# 在浏览器中打开最新的仓库
gh repo view --web
```

## ⚙️ 自动化配置

已经为你配置了两个自动化任务：

1. **每日热点项目生成** - 每天早上 9:00 自动运行
2. **每日指标监控** - 每天晚上 20:00 自动更新指标

你可以在 WorkBuddy 的"自动化"页面查看和管理这些任务。

## 🎨 自定义配置

### 修改热点来源

编辑 `config.yaml`：

```yaml
sources:
  - name: "web_search"
    enabled: true
    keywords:
      - "AI breakthrough 2026"
      - "LLM new release"
      - "AI agent framework"
      # 添加你自己的关键词
```

### 修改项目类型

编辑 `config.yaml`：

```yaml
generator:
  tech_stacks:
    - name: "python_tool"      # 优先使用 Python 工具
    - name: "web_app"          # 或 Web 应用
    - name: "full_stack"       # 或全栈应用
```

### 修改监控指标

编辑 `config.yaml`：

```yaml
monitor:
  metrics:
    - "stars"
    - "forks"
    - "watchers"
    - "issues"
    # 添加你想追踪的指标
```

## 🐛 常见问题

### Q: GitHub CLI 认证失败？

```bash
# 重新登录
gh auth logout
gh auth login
```

### Q: 无法推送到 GitHub？

```bash
# 检查 Git 配置
git config --global user.name
git config --global user.email

# 设置 Git 凭证
gh auth setup-git
```

### Q: 项目生成失败？

```bash
# 查看详细日志
cat data/logs/agent.log

# 检查磁盘空间
df -h  # Linux/Mac
# 或检查 Windows 磁盘空间
```

### Q: 如何停止自动化？

在 WorkBuddy 的"自动化"页面，找到对应的任务，点击"暂停"。

## 📊 建立个人 IP 的技巧

1. **保持一致性** - 每天都发布，展示你的坚持
2. **高质量代码** - 每个项目都有完整的文档和测试
3. **积极参与** - 回复 issues 和 PRs，建立社区
4. **分享进展** - 在社交媒体分享你的项目
5. **持续优化** - 根据反馈改进你的 Agent

## 🎯 下一步

- 运行 `python setup_check.py` 验证配置
- 运行 `python agent.py` 测试第一个项目
- 检查生成的项目质量
- 配置自动化任务
- 开始建立你的 AI 项目 Portfolio！

## 📚 更多资源

- [GitHub CLI 文档](https://cli.github.com/manual/)
- [GitHub Token 创建](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [WorkBuddy 自动化文档](https://www.workbuddy.com/docs/automation)

---

祝你建立强大的个人技术品牌！🚀
