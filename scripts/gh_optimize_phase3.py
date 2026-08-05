#!/usr/bin/env python3
"""Phase-3 optimization: account-level community health files (.github repo),
LICENSE completion, loopforge CI workflow and FUNDING.yml, all via Contents API.

Why this script exists: local git transport to github.com is reset in this
environment, but api.github.com is reachable. The GitHub *Contents API*
(PUT /repos/{o}/{r}/contents/{p}) is the right tool for single-file
create/update pushes, bypassing git smart-HTTP entirely.

No token is hardcoded: it is read from config.yaml at runtime.
"""
import re
import json
import base64
import time
import urllib.request
import urllib.error

CFG = open("config.yaml", encoding="utf-8").read()
TOKEN = re.search(r'token:\s*"([^"]+)"', CFG).group(1)
USER = "huzjie"
API_ROOT = "https://api.github.com"

results = []  # (status, repo, path, detail)


def _req(method, url, data=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-agent",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        return json.dumps({"_error": e.code, "detail": e.read().decode()[:300]})


def api(method, url, data=None):
    return json.loads(_req(method, API_ROOT + url, data))


def default_branch(repo):
    info = api("GET", f"/repos/{USER}/{repo}")
    return info.get("default_branch", "main")


def create_or_update_file(repo, path, content, message):
    """Create or update a single file on the default branch via Contents API."""
    branch = default_branch(repo)
    cur = api("GET", f"/repos/{USER}/{repo}/contents/{path}?ref={branch}")
    sha = cur.get("sha") if isinstance(cur, dict) else None
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode(),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    res = api("PUT", f"/repos/{USER}/{repo}/contents/{path}", payload)
    status = "updated" if sha else "created"
    ok = isinstance(res, dict) and ("content" in res or "commit" in res)
    detail = "OK" if ok else f"FAIL {json.dumps(res, ensure_ascii=False)[:200]}"
    results.append((status, repo, path, detail))
    print(f"  [{status}] {repo}/{path} -> {detail}")
    return ok


# ---------------- standard license texts ----------------
APACHE_LICENSE = """Copyright 2026 huzjie

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

MIT_LICENSE = """MIT License

Copyright (c) 2026 huzjie

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# ---------------- account-level default community health files ----------------
CONTRIBUTING_MD = """# 贡献指南（Contributing Guide）

感谢你愿意为 huzjie 组织下的开源项目贡献代码！这份指南帮助你和维护者高效协作。

## 如何开始

1. **Fork 仓库**：点击页面右上角 Fork，将仓库复制到你的账号下。
2. **Clone 到本地**：`git clone https://github.com/<你的用户名>/<仓库名>.git`
3. **创建分支**：`git checkout -b feat/my-feature`（分支命名建议：`feat/`、`fix/`、`docs/`、`chore/`）
4. **本地开发**：按照仓库 README 的 Quick Start 安装依赖并启动。
5. **提交 PR**：推送分支后，在 GitHub 上发起 Pull Request，描述变更内容。

## 开发规范

- **Python 项目**：使用 `ruff` / `black` 保持代码风格统一；新增功能需补充类型注解与 docstring。
- **TypeScript 项目**：遵循 ESLint + Prettier 配置。
- 提交前运行测试：`pytest -q`（Python）或 `npm test`（TypeScript）。

## Commit 规范

使用 Conventional Commits 风格：

- `feat: 新增功能`
- `fix: 修复缺陷`
- `docs: 文档变更`
- `refactor: 重构（不改变行为）`
- `test: 测试相关`
- `chore: 构建 / 工具链变更`

示例：`feat(auth): add api key rotation`

## Issue 流程

- **Bug 报告**：使用 Bug Report 模板，包含复现步骤、期望行为、实际行为与环境信息。
- **功能建议**：使用 Feature Request 模板，说明使用场景与期望能力。
- 维护者会在 48 小时内响应（工作时间）。

## PR 审查

- 所有 PR 需通过 CI 检查。
- 行为变更需附测试；纯文档变更可豁免。
- 保持 PR 小而聚焦，一个 PR 解决一个问题。

## 行为准则

参与本项目即表示你同意遵循 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

再次感谢你的贡献！
"""

CODE_OF_CONDUCT_MD = """# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity
and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment for our
community include:

* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes,
  and learning from the experience
* Focusing on what is best not just for us as individuals, but for the
  overall community

Examples of unacceptable behavior include:

* The use of sexualized language or imagery, and sexual attention or
  advances of any kind
* Trolling, insulting or derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or email
  address, without their explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior that they deem inappropriate, threatening, offensive,
or harmful.

Community leaders have the right and responsibility to remove, edit, or reject
comments, commits, code, wiki edits, issues, and other contributions that are
not aligned to this Code of Conduct, and will communicate reasons for moderation
decisions when appropriate.

## Scope

This Code of Conduct applies within all community spaces, and also applies when
an individual is officially representing the community in public spaces.
Examples of representing our community include using an official e-mail address,
posting via an official social media account, or acting as an appointed
representative at an online or offline event.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement at
huzjie@users.noreply.github.com.

All complaints will be reviewed and investigated promptly and fairly.

All community leaders are obligated to respect the privacy and security of the
reporter of any incident.

## Enforcement Guidelines

Community leaders will follow these Community Impact Guidelines in determining
the consequences for any action they deem in violation of this Code of Conduct:

### 1. Correction

**Community Impact**: Use of inappropriate language or other behavior deemed
unprofessional or unwelcome in the community.

**Consequence**: A private, written warning from community leaders, providing
clarity around the nature of the violation and an explanation of why the
behavior was inappropriate. A public apology may be requested.

### 2. Warning

**Community Impact**: A violation through a single incident or series of
actions.

**Consequence**: A warning with consequences for continued behavior. No
interaction with the people involved, including unsolicited interaction with
those enforcing the Code of Conduct, for a specified period of time. This
includes avoiding interactions in community spaces as well as external channels
like social media. Violating these terms may lead to a temporary or permanent ban.

### 3. Temporary Ban

**Community Impact**: A serious violation of community standards, including
sustained inappropriate behavior.

**Consequence**: A temporary ban from any sort of interaction or public
communication with the community for a specified period of time. No public or
private interaction with the people involved, including unsolicited interaction
with those enforcing the Code of Conduct, is allowed during this period.
Violating these terms may lead to a permanent ban.

### 4. Permanent Ban

**Community Impact**: Demonstrating a pattern of violation of community
standards, including sustained inappropriate behavior, harassment of an
individual, or aggression toward or disparagement of classes of individuals.

**Consequence**: A permanent ban from any sort of public interaction within
the community.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage],
version 2.1, available at
https://www.contributor-covenant.org/version/2/1/code_of_conduct.html.

Community Impact Guidelines were inspired by
[Mozilla's code of conduct enforcement ladder][Mozilla CoC].

For answers to common questions about this code of conduct, see the FAQ at
https://www.contributor-covenant.org/faq. Translations are available at
https://www.contributor-covenant.org/translations.

[homepage]: https://www.contributor-covenant.org
[Mozilla CoC]: https://github.com/mozilla/diversity

Copyright (c) 2026 huzjie. All rights reserved.
"""

SECURITY_MD = """# 安全策略（Security Policy）

## 支持的版本

| 版本 | 支持状态 |
| --- | --- |
| main 分支 | ✅ 积极维护 |
| 历史 Release | 仅修复高危安全问题 |

## 报告漏洞

如果你发现安全漏洞，**请不要公开 Issue**，请通过以下方式私下报告：

- 邮箱：huzjie@users.noreply.github.com（标题前缀 `[SECURITY]`）
- GitHub Security Advisory：仓库页面 → Security → Report a vulnerability

## 响应时间

- 确认收到报告：**24 小时内**
- 漏洞评估与首次回复：**48 小时内**
- 修复版本发布：视严重程度而定，高危漏洞优先处理

## 安全最佳实践

- 不要将 API Key / Token 提交到仓库，一律使用环境变量或密钥管理服务。
- 若误提交密钥，请立即轮换并联系维护者清理历史。
"""

FUNDING_YML = "github: [huzjie]\n"

PR_TEMPLATE_MD = """## 变更描述（Description）

请简要描述本次 PR 解决了什么问题、做了哪些变更。

## 自检清单（Checklist）

- [ ] 我已阅读并遵循 [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [ ] 变更已通过本地测试（`pytest -q` / `npm test`）
- [ ] 文档已同步更新（README / docs）
- [ ] 无破坏性变更；如有，已在下方说明迁移方案

## 测试（Testing）

描述你做了哪些测试，以及如何复现。

## 破坏性变更（Breaking Changes）

如无，请填"无"。

## 关联 Issue

Closes #<issue-number>
"""

BUG_REPORT_MD = """---
name: Bug 报告
about: 提交缺陷，帮助我们改进
title: "[Bug] "
labels: bug
assignees: ''
---

## 描述（Description）

请清晰描述这个 bug 是什么。

## 复现步骤（To Reproduce）

1. 执行 `...`
2. 输入 `...`
3. 看到报错 `...`

## 期望行为（Expected behavior）

...

## 实际行为（Actual behavior）

...

## 环境（Environment）

- 操作系统：
- Python / Node 版本：
- 关键依赖版本（可贴 requirements / pyproject 片段）：

## 日志 / 截图（Logs / Screenshots）

"""

FEATURE_REQUEST_MD = """---
name: 功能建议
about: 提出新功能或改进建议
title: "[Feature] "
labels: enhancement
assignees: ''
---

## 使用场景（Use case）

你希望在什么场景下使用这个功能？

## 期望能力（Proposed behavior）

请描述你期望的功能行为。

## 备选方案（Alternatives）

你考虑过哪些替代方案？

## 附加信息（Additional context）

"""

DEPENDABOT_YML = """version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      dependencies:
        patterns: ["*"]
"""

# ---------------- loopforge CI workflow ----------------
CI_YML = """name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e . -r requirements-dev.txt pytest
      - name: Run tests
        run: pytest -q
"""


def ensure_github_repo():
    """Create the public .github repo if missing; returns True when it exists."""
    st = api("GET", f"/repos/{USER}/.github")
    if isinstance(st, dict) and st.get("full_name"):
        print("[skip] .github 仓库已存在")
        return True
    payload = {
        "name": ".github",
        "description": "Default community health files for all huzjie repositories",
        "private": False,
        "auto_init": True,
    }
    res = api("POST", "/user/repos", payload)
    if isinstance(res, dict) and res.get("full_name"):
        print("[created] .github 仓库创建成功")
        return True
    # 422 etc: double-check existence (maybe created concurrently)
    chk = api("GET", f"/repos/{USER}/.github")
    if isinstance(chk, dict) and chk.get("full_name"):
        print("[exists] .github 仓库已存在（创建返回非 2xx，但 GET 确认存在）")
        return True
    print(f"[failed] .github 仓库创建失败: {json.dumps(res, ensure_ascii=False)[:300]}")
    results.append(("failed", ".github", "(repo)", str(res)[:200]))
    return False


def main():
    print("=== Phase 3: 账号级社区健康文件 + LICENSE + CI + FUNDING ===")

    # 1. .github repo + default community health files
    print("--- 1. .github 仓库（账号级默认社区健康文件）---")
    if ensure_github_repo():
        time.sleep(2)  # let the new repo settle
        files = [
            ("CONTRIBUTING.md", CONTRIBUTING_MD, "docs: 账号级默认贡献指南"),
            ("CODE_OF_CONDUCT.md", CODE_OF_CONDUCT_MD, "docs: 账号级默认行为准则（Contributor Covenant 2.1）"),
            ("SECURITY.md", SECURITY_MD, "docs: 账号级默认安全策略"),
            ("FUNDING.yml", FUNDING_YML, "docs: 开启 Sponsor 按钮"),
            ("PULL_REQUEST_TEMPLATE.md", PR_TEMPLATE_MD, "docs: 账号级默认 PR 模板"),
            ("ISSUE_TEMPLATE/bug_report.md", BUG_REPORT_MD, "docs: 账号级默认 Bug 报告模板"),
            ("ISSUE_TEMPLATE/feature_request.md", FEATURE_REQUEST_MD, "docs: 账号级默认功能建议模板"),
            ("dependabot.yml", DEPENDABOT_YML, "ci: 账号级默认 pip 依赖更新策略"),
        ]
        for path, content, msg in files:
            create_or_update_file(".github", path, content, msg)

    # 2. LICENSE 补全（4 个仓库）
    print("--- 2. LICENSE 补全 ---")
    create_or_update_file("moe-bench-studio", "LICENSE", APACHE_LICENSE,
                          "chore(license): 替换为完整 Apache-2.0 许可证文本")
    create_or_update_file("unified-ai-gateway", "LICENSE", APACHE_LICENSE,
                          "chore(license): 替换为完整 Apache-2.0 许可证文本")
    create_or_update_file("ai-daily-agent", "LICENSE", MIT_LICENSE,
                          "chore(license): 新增 MIT 许可证")
    create_or_update_file("ai-daily-hub", "LICENSE", MIT_LICENSE,
                          "chore(license): 新增 MIT 许可证")

    # 3. loopforge CI workflow
    print("--- 3. loopforge CI ---")
    create_or_update_file("loopforge", ".github/workflows/ci.yml", CI_YML,
                          "ci: 新增 GitHub Actions（push main + PR 触发，pytest）")

    # 4. 旗舰仓库 FUNDING.yml（unified-ai-gateway 已存在，跳过）
    print("--- 4. 旗舰仓库 FUNDING.yml ---")
    for repo in ["loopforge", "moe-bench-studio", "argus-eval"]:
        create_or_update_file(repo, ".github/FUNDING.yml", FUNDING_YML,
                              "docs: 开启 Sponsor 按钮")
    results.append(("skipped", "unified-ai-gateway", ".github/FUNDING.yml", "已存在，跳过"))

    # 5. Star 引导文案：4 个旗舰 README 均已含 Star 字样，跳过
    results.append(("skipped", "loopforge", "README Star 文案", "README 已有 Star 字样"))
    results.append(("skipped", "moe-bench-studio", "README Star 文案", "README 已有 Star 字样"))
    results.append(("skipped", "argus-eval", "README Star 文案", "README 已有 Star 字样"))
    results.append(("skipped", "unified-ai-gateway", "README Star 文案", "README 已有 Star 字样"))

    # 6. 复核 LICENSE 识别
    print("--- 5. 复核 LICENSE 识别 ---")
    time.sleep(3)
    for repo in ["moe-bench-studio", "unified-ai-gateway", "ai-daily-agent", "ai-daily-hub"]:
        info = api("GET", f"/repos/{USER}/{repo}")
        lic = (info.get("license") or {}).get("spdx_id")
        print(f"  license {repo} -> spdx_id={lic}")
        results.append(("verify", repo, "license.spdx_id", str(lic)))

    # summary
    print("\n=== 汇总 ===")
    from collections import Counter
    cnt = Counter(r[0] for r in results)
    print(f"created={cnt.get('created', 0)} updated={cnt.get('updated', 0)} "
          f"skipped={cnt.get('skipped', 0)} failed={cnt.get('failed', 0)} "
          f"verify={cnt.get('verify', 0)}")
    for st, repo, path, detail in results:
        print(f"  {st:<8} {repo}/{path}  {detail[:120]}")


if __name__ == "__main__":
    main()
