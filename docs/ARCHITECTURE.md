# AI Daily Agent - 项目架构说明

## 系统概述

AI Daily Agent 是一个全自动的 AI 热点追踪和项目生成系统，采用模块化设计，便于扩展和维护。

## 核心模块

### 1. HotTopicDiscoverer (热点发现模块)

**职责**: 从多个来源发现和追踪 AI 热点话题

**工作流程**:
```
1. 从配置中读取数据源
2. 并行查询各个数据源
   - Web Search (SerpAPI/Google)
   - GitHub Trending
   - Hugging Face Models
3. 去重和排序
4. 返回 Top N 热点
```

**扩展方式**:
- 添加新的数据源方法 `_discover_from_new_source()`
- 在 `config.yaml` 中配置新的 source
- 实现对应的解析逻辑

### 2. ProjectGenerator (项目生成模块)

**职责**: 基于热点生成完整的、生产可用的项目

**工作流程**:
```
1. 分析热点特征
2. 选择最佳技术栈
3. 创建项目结构
4. 生成源代码
5. 生成文档 (README, CONTRIBUTING, CHANGELOG)
6. 生成测试
7. 生成 CI/CD 配置
8. 生成 Docker 配置
```

**技术栈选择逻辑**:
- 基于热点关键词匹配
- 基于标签评分
- 默认回退到 Python 工具

**扩展方式**:
- 添加新的技术栈模板
- 实现 `_generate_xxx_code()` 方法
- 在 `tech_stacks` 配置中注册

### 3. GitHubPublisher (GitHub 发布模块)

**职责**: 将生成的项目发布到 GitHub

**工作流程**:
```
1. 检查 GitHub 认证
2. 初始化 Git 仓库
3. 创建 GitHub 仓库
4. 推送代码
5. 更新 Hub 仓库（索引仓库）
6. 记录发布历史
```

**安全措施**:
- 使用 Personal Access Token
- 最小权限原则
- 发布历史记录

**扩展方式**:
- 支持更多 Git 平台（GitLab, Bitbucket）
- 添加自动 Release 功能
- 集成更多 CI/CD 功能

### 4. RepoMonitor (仓库监控模块)

**职责**: 追踪已发布仓库的指标和增长

**工作流程**:
```
1. 从 GitHub API 获取指标
2. 记录到历史数据
3. 计算增长趋势
4. 生成报告
5. 检测里程碑
```

**追踪指标**:
- Stars
- Forks
- Watchers
- Issues
- Commits

**扩展方式**:
- 添加新的指标
- 集成通知系统（邮件、Slack、Discord）
- 添加可视化图表

## 数据流

```
config.yaml
    ↓
AIDailyAgent (主协调器)
    ↓
    ├─→ HotTopicDiscoverer
    │       ↓
    │   List[HotTopic]
    │       ↓
    ├─→ ProjectGenerator
    │       ↓
    │   Project Directory
    │       ↓
    ├─→ GitHubPublisher
    │       ↓
    │   GitHub Repository
    │       ↓
    └─→ RepoMonitor
            ↓
        Metrics Report
```

## 目录结构

```
ai-daily-agent/
├── agent.py                    # 主入口和协调器
├── config.yaml                 # 全局配置
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
├── .env                        # 实际环境变量（不提交）
├── .gitignore                  # Git 忽略规则
│
├── src/                        # 源代码
│   ├── __init__.py
│   ├── discoverer/             # 热点发现
│   │   ├── __init__.py
│   │   └── hot_topic_discoverer.py
│   ├── generator/              # 项目生成
│   │   ├── __init__.py
│   │   └── project_generator.py
│   ├── publisher/              # GitHub 发布
│   │   ├── __init__.py
│   │   └── github_publisher.py
│   └── monitor/                # 数据监控
│       ├── __init__.py
│       └── repo_monitor.py
│
├── data/                       # 运行时数据
│   ├── projects/               # 生成的项目
│   ├── logs/                   # 运行日志
│   ├── metrics/                # 指标数据
│   └── reports/                # 报告文件
│
├── templates/                  # 项目模板（预留）
├── docs/                       # 文档
└── tests/                      # 测试
```

## 配置系统

### config.yaml 结构

```yaml
# 应用基础配置
app:
  name: "AI Daily Agent"
  version: "1.0.0"
  timezone: "Asia/Shanghai"

# GitHub 配置
github:
  username: ""                  # GitHub 用户名
  token: ""                     # Personal Access Token
  repo_prefix: "ai-daily-"      # 仓库名前缀
  branch: "main"                # 默认分支
  visibility: "public"          # 仓库可见性

# 数据源配置
sources:
  - name: "web_search"          # 网络搜索
    enabled: true
    keywords: []                # 搜索关键词
    max_topics: 5               # 最大主题数
  
  - name: "github_trending"     # GitHub Trending
    enabled: true
    languages: []               # 编程语言
    since: "daily"              # 时间范围

  - name: "huggingface"         # Hugging Face
    enabled: true
    model_types: []             # 模型类型

# 项目生成配置
generator:
  tech_stacks:                  # 技术栈列表
    - name: "python_tool"
      description: "Python CLI tool or library"
      language: "python"
      template: "python_project"
    # ... 更多技术栈
  
  readme:                       # README 配置
    include_badges: true
    include_demo: true
    include_architecture: true
    include_screenshots_placeholder: true
    include_benchmark: true
    languages: ["zh-CN", "en"]  # 多语言支持
  
  quality:                      # 质量门控
    must_have_tests: true
    must_have_dockerfile: true
    must_have_ci: true
    min_readme_length: 500

# 监控配置
monitor:
  metrics:                      # 追踪的指标
    - "stars"
    - "forks"
    - "watchers"
    - "issues"
    - "commits"
  
  notifications:                # 通知设置
    enabled: true
    on_star_milestone: true
    star_milestones: [1, 5, 10, 50, 100]

# 日志配置
logging:
  level: "INFO"
  file: "data/logs/agent.log"
  max_size_mb: 10
  backup_count: 30
```

## 错误处理

系统采用多层次错误处理：

1. **模块级错误处理**: 每个模块独立处理自己的错误
2. **协调器级错误处理**: 主流程捕获并记录错误
3. **日志记录**: 所有错误都记录到日志文件
4. **优雅降级**: 某些步骤失败不影响整体流程

## 性能优化

1. **并行处理**: 多个数据源可以并行查询
2. **缓存机制**: 热点发现结果会缓存
3. **增量更新**: 监控只更新变化的指标
4. **懒加载**: 按需加载模块和配置

## 安全性

1. **环境变量**: 敏感信息使用 `.env` 文件
2. **最小权限**: GitHub Token 只需要 repo 权限
3. **代码审查**: 生成的代码应该经过审查
4. **日志脱敏**: 日志中不包含敏感信息

## 扩展指南

### 添加新的数据源

1. 在 `HotTopicDiscoverer` 中添加新方法
2. 在 `config.yaml` 中配置新的 source
3. 实现解析逻辑

### 添加新的项目模板

1. 在 `ProjectGenerator` 中添加新方法
2. 在 `tech_stacks` 中注册新模板
3. 实现代码生成逻辑

### 添加新的通知渠道

1. 在 `RepoMonitor` 中添加通知方法
2. 在 `config.yaml` 中配置通知设置
3. 实现通知发送逻辑

## 未来计划

- [ ] 集成 LLM 生成更智能的代码
- [ ] 支持更多 Git 平台
- [ ] 添加可视化仪表板
- [ ] 集成社交媒体自动发布
- [ ] 支持自定义项目模板
- [ ] 添加 A/B 测试功能
- [ ] 集成代码质量检查
- [ ] 添加自动修复功能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
