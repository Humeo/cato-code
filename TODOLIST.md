# RepoCraft v2 — Autonomous Codebase Maintenance Agent

## Vision

一个长时运行的代码库维护助手 — 像一个虚拟团队成员, 被分配到一个仓库后:

1. **主动发现问题**: 定期扫描代码库, 发现 bug、安全漏洞、过时依赖、
   缺失测试、代码异味, 自己创建 issue 或直接修复
2. **响应事件**: 新 issue、PR review、CI 失败 — 自动接手处理
3. **接受指令**: 开发者可以直接 @它 或 CLI 告诉它做事 —
   "加个缓存层"、"查下为什么这个接口慢"、"重构认证模块"
4. **自主工作数小时**, 迭代测试直到有信心
5. **返回可审查的产物**: logs、截图、录屏、live preview — 而不只是 diffs

### 三种触发方式

```
主动发现    Scheduler 定期触发 scan activity → Agent 扫描 repo → 发现问题 → 修复/报告
事件响应    GitHub event (issue/review/@mention) → 自动创建 activity → Agent 处理
人类指令    CLI `repocraft ask "加个功能"` 或 GitHub @repocraft → Agent 执行
```

### Activity Kinds

| Kind | 触发 | Agent 做什么 |
|------|------|-------------|
| `init` | 新 repo 首次 | 探索仓库, 生成 repo-specific CLAUDE.md |
| `fix_issue` | issue / 人类指令 | 理解 → 修复 → 测试 → 提 PR |
| `task` | 人类指令 (@mention / CLI) | 执行任意任务: 加功能、查问题、重构 |
| `scan` | 定时 (每天/每周) | 全面扫描: 安全、依赖、测试覆盖、代码质量 → issue/PR |
| `respond_review` | PR review event | 读 review → 修改 → push |
| `triage` | 新 issue event | 评估复杂度 → 回复 → 打 label → 可选自动修 |

### Vision Alignment

| 愿景要素 | 方案如何实现 | 交付 |
|----------|-------------|------|
| 自主发现问题 | scan activity (定期) + triage (事件) | M4 |
| 接受人类指令 | `repocraft ask` CLI + GitHub @mention 检测 | M2 |
| 响应 GitHub 事件 | daemon watch + event polling | M4 |
| 长时自主工作 | `claude -p --max-turns 200`, 可跑数小时 | M1 |
| 隔离运行 | 常驻 Docker 容器, OS 级隔离 | M0 |
| 交任务就走 | `repocraft submit/ask` + daemon 后台 | M2 |
| Logs | `--output-format stream-json` + `repocraft logs --follow` | M1 |
| 视频录制 | Playwright 录屏, 附到 PR | M5 |
| Live Previews | Dev server + cloudflared tunnel | M5 |
| 不只是 diffs | Agent 直接 `gh pr create`, PR 含测试输出+截图 | M1 |

---

## Architecture

```
Host (你的物理机)
├── repocraft (单进程 Python CLI)
│   ├── CLI: fix / submit / daemon / status / logs
│   ├── Scheduler: poll DB → dispatch workers
│   ├── Dispatcher: docker exec → claude -p → stream logs to DB
│   └── SQLite: repos, activities, logs
│
└── Docker Container "repocraft-worker" (常驻)
    ├── ~/.claude/CLAUDE.md        ← 用户级: 所有 repo 通用的 agent 规则
    ├── claude CLI                 ← 自带 Bash/Edit/Read/Write/Grep/Glob
    ├── git, gh, python, node, uv
    ├── /repos/
    │   ├── owner-repo-a/
    │   │   ├── CLAUDE.md          ← repo 级: init 阶段由 agent 探索生成
    │   │   ├── .claude/memory/    ← auto-memory: Claude Code 自动维护
    │   │   └── src/...
    │   └── owner-repo-b/
    │       └── ...
    └── /output/                   ← 截图、录屏等产物 (volume mount)
```

### CLAUDE.md 两层设计

**用户级 `~/.claude/CLAUDE.md`** (容器内, 对所有 repo 生效):
所有 repo 都遵循的规则 — workflow, 安全规则, 行为约束。
由 RepoCraft 在容器初始化时写入, 不由 agent 修改。

**Repo 级 `/repos/{repo}/CLAUDE.md`** (每个 repo 目录内):
repo 特有的知识 — 架构, 测试命令, 代码风格, 关键文件。
由 agent 在 init 阶段探索 repo 后自动生成, 后续 activity 中持续更新。

### 一次 Activity 的执行

```bash
docker exec repocraft-worker bash -c '
  cd /repos/{repo_id} &&
  git fetch origin && git checkout main && git reset --hard origin/main && git clean -fdx &&
  claude -p "<task prompt>" \
    --output-format stream-json \
    --dangerously-skip-permissions \
    --max-turns 200 \
    --verbose
'
```

- Claude Code 自动读 ~/.claude/CLAUDE.md (通用规则) + ./CLAUDE.md (repo 知识)
- Agent 自主完成: 理解 → 修复 → 测试 → commit → push → gh pr create
- Dispatcher 只需看 exit code: 0=成功, 非0=失败
- 不需要解析 PR URL — agent 在容器内直接用 gh 创建 PR

---

## Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 引擎 | Claude Code CLI (`claude -p`) | 自带所有工具, 不需要自己造 |
| 隔离 | 单常驻 Docker 容器, repo=目录 | Pattern 2: OS 级隔离 |
| 权限 | `--dangerously-skip-permissions` | 容器内安全, 官方推荐 |
| 通用规则 | `~/.claude/CLAUDE.md` (容器内) | 所有 repo 共享, 用户级 |
| Repo 记忆 | `./CLAUDE.md` + `.claude/memory/` | 原生支持, 零代码, init 阶段生成 |
| 完成信号 | `claude -p` exit code | 不解析输出, 不提取 PR URL |
| 日志 | `--output-format stream-json` → SQLite | 实时流 + 持久化 |
| Session | 默认独立; respond_review 用 `--resume` | 简单, 特殊情况续接 |
| 并发 | asyncio.Semaphore + per-repo Lock | 全局上限 + repo 串行 |
| Git auth | GITHUB_TOKEN 环境变量 + credential helper | 容器启动时传入 |
| Claude Code 更新 | 容器联网, 启动时自动更新 | 始终最新版 |
| 超时 | `--max-turns 200` + scheduler 2h 硬杀 | 两层防护 |

---

## Risks

### R1: Agent 无限循环烧钱 [高]

三层防护:
1. `--max-turns 200` — Claude Code 内置
2. 用户级 CLAUDE.md: "5 次尝试失败即停止"
3. Scheduler: `asyncio.wait_for(timeout=7200)` — 2h 硬杀

### R2: Agent push 坏代码 [高]

- 用户级 CLAUDE.md: "push 前必须测试通过"
- 只走 PR, 不直接 push main
- 人类仍可 review PR
- 可选: GitHub branch protection rules

### R3: GITHUB_TOKEN 泄露 [高]

- 容器启动时环境变量传入, 不落盘
- git credential helper 读取环境变量
- 用户级 CLAUDE.md: "绝不打印 credentials"

### R4: 容器磁盘满 [中]

- Docker volume 大小限制
- 用户级 CLAUDE.md: "结束时清理 build artifacts"
- `repocraft cleanup` 命令

### R5: Git 状态损坏 [中]

- 每次 activity 前: `git reset --hard origin/main && git clean -fdx`
- Per-repo Lock 确保串行
- 最坏: `rm -rf && git clone` 重来

### R6: Claude Code 进程挂死 [中]

- `asyncio.wait_for` + kill
- 备选: activity-aware timeout (无输出 10 分钟即杀)

---

## TODOLIST

### Milestone 0: 基础设施

- [ ] 0.1 构建容器镜像 (Dockerfile)
  - 基于 Ubuntu 24.04
  - 安装: git, curl, wget, build-essential, ca-certificates
  - 安装: Python 3.12 + uv
  - 安装: Node.js 22 LTS + npm
  - 安装: Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
  - 安装: GitHub CLI (`gh`)
  - 配置: git credential helper (读 GITHUB_TOKEN 环境变量)
  - 配置: git user.name="RepoCraft" user.email="repocraft@bot"
  - Tag: repocraft-worker:v1
  - 验证: docker run → claude --version, gh --version, python3 --version

- [ ] 0.2 用户级 CLAUDE.md 模板 (templates/user_claude_md.py)
  - 写入容器的 ~/.claude/CLAUDE.md
  - 内容: 通用 agent 规则 (workflow, safety rules, branch naming)
  - 在容器首次创建时写入

- [ ] 0.3 容器管理器 (container/manager.py 重写)
  - `ensure_running()`:
    - 检查 `repocraft-worker` 容器状态
    - 不存在 → 创建 (volumes: repocraft-repos→/repos, repocraft-output→/output)
    - 传入: ANTHROPIC_API_KEY, GITHUB_TOKEN
    - 存在但停了 → docker start
    - 存在且运行 → 返回
    - 首次创建后写入用户级 CLAUDE.md
  - `exec(command, workdir) -> ExecResult`
  - `exec_stream(command, workdir) -> AsyncIterator[str]` (逐行 yield)
  - `ensure_repo(repo_id, repo_url)`:
    - /repos/{repo_id}/ 不存在 → git clone --depth=50
    - 已存在 → 跳过
  - `reset_repo(repo_id)`:
    - git fetch origin
    - 检测默认分支 (main or master)
    - git checkout {default} && git reset --hard origin/{default} && git clean -fdx
  - `stop()`: docker stop (不 remove, 保留 volume)
  - 资源: 8GB RAM, 4 CPU (环境变量 REPOCRAFT_MEM / REPOCRAFT_CPUS)

- [ ] 0.4 SQLite store (store.py)
  - Tables:
    ```
    repos(id, repo_url, created_at)
    activities(id, repo_id, kind, trigger, status, session_id,
               summary, created_at, updated_at)
    logs(id, activity_id, line, ts)
    ```
  - status: pending → running → done | failed
  - kind: init | fix_issue | task | scan | respond_review | triage
  - CRUD methods
  - DB 路径: ~/.repocraft/repocraft.db

### Milestone 1: 单 Activity 端到端 (`repocraft fix`)

- [ ] 1.1 Repo Init Activity
  - 新 repo clone 后, 自动运行 init:
    ```
    claude -p "探索这个仓库, 理解其结构、架构、测试方式、构建方式、
    代码风格, 然后写一个 CLAUDE.md 到项目根目录, 记录你的发现。
    包括: 架构概述, 测试命令, 构建命令, 关键文件路径, 代码约定。" \
      --dangerously-skip-permissions \
      --max-turns 30 \
      --output-format stream-json
    ```
  - Init 完成后, repo 目录下有 agent 生成的 CLAUDE.md
  - Init 是 activity kind="init", 记录到 DB
  - 后续所有 activity 都受益于这个 CLAUDE.md

- [ ] 1.2 Dispatcher (dispatcher.py)
  - `async def dispatch(activity, store, container_mgr)`:
    1. `container_mgr.ensure_running()`
    2. `container_mgr.ensure_repo(repo_id, repo_url)`
    3. 如果是新 repo (无 CLAUDE.md) → 先跑 init activity
    4. `container_mgr.reset_repo(repo_id)`
    5. 构造 prompt:
       - fix_issue: issue title + body + comments + "修复这个 issue 并提 PR"
       - task: 用户的自由文本指令 (如 "加个缓存层", "查下内存泄漏")
       - scan: "全面审查这个代码库, 找出 bug/安全问题/过时依赖/缺失测试, 为每个发现创建 issue 或直接修复"
       - respond_review: PR review comments + "根据 review 修改代码并 push"
       - triage: issue content + "评估这个 issue, 回复你的分析"
    6. 构造 claude 命令:
       ```
       cd /repos/{repo_id} && claude -p {prompt} \
         --output-format stream-json \
         --dangerously-skip-permissions \
         --max-turns 200 \
         --verbose
       ```
    7. exec_stream → 逐行写 store.add_log()
    8. 进程退出 → exit_code 决定 status (0=done, else=failed)
    9. `store.update_activity(status=..., summary=最后几行输出)`
  - 超时: `asyncio.wait_for(timeout=7200)`
  - 异常: 捕获 → status="failed"

- [ ] 1.3 CLI: `repocraft fix <issue_url>`
  - argparse 子命令
  - 解析 URL → (owner, repo, issue_number)
  - fetch issue (复用 github/issue_fetcher.py)
  - store.add_repo() if not exists
  - store.add_activity(kind="fix_issue", trigger=f"issue:{number}")
  - await dispatch(activity) — 阻塞, 实时打印日志到终端
  - 结束时打印 status + summary
  - 选项: --model, --max-turns, --verbose

- [ ] 1.4 端到端验证
  - 创建测试 repo: 简单 Python 项目 + 一个 known bug issue
  - `repocraft fix https://github.com/you/test-repo/issues/1`
  - 验证:
    - [ ] init 阶段生成了 repo-specific CLAUDE.md
    - [ ] Agent 理解了 issue
    - [ ] Agent 修复了 bug
    - [ ] Agent 跑了测试
    - [ ] Agent 创建了 PR (via gh)
    - [ ] PR description 包含测试输出
    - [ ] activity status = done
    - [ ] 日志被写入 DB

### Milestone 2: 后台调度 + 多 Activity

- [ ] 2.1 Scheduler (scheduler.py)
  ```
  MAX_WORKERS = env REPOCRAFT_MAX_WORKERS (default 3)

  run_forever():
    恢复: running → failed (上次 crash)
    loop:
      pending = get_pending_activities()
      for each pending:
        if repo locked → skip
        if semaphore full → skip
        spawn task: acquire sem → acquire repo lock → dispatch → release
      sleep 10s
  ```

- [ ] 2.2 CLI: `repocraft daemon`
  - 前台启动 scheduler
  - ensure_running() 容器
  - SIGTERM/SIGINT graceful shutdown

- [ ] 2.3 CLI: `repocraft submit <issue_url>`
  - 解析 URL, 写 DB (status=pending), 打印 activity_id
  - 不执行, daemon 后台处理
  - 选项: --kind (fix_issue/triage/respond_review)

- [ ] 2.4 CLI: `repocraft ask <repo> "<instruction>"`
  - 直接给 agent 下达任意指令
  - 例: `repocraft ask owner/repo "加一个 rate limiter 到 API 层"`
  - 例: `repocraft ask owner/repo "查下为什么 /users 接口响应慢"`
  - 例: `repocraft ask owner/repo "把认证从 session 迁移到 JWT"`
  - 创建 activity(kind="task", trigger=instruction)
  - 默认阻塞执行 (加 --async 则入队交给 daemon)

- [ ] 2.4 CLI: `repocraft status [repo_id | activity_id]`
  - 无参: 所有 repo + 活跃 activity 列表
  - repo_id: 该 repo 的 activity 列表
  - activity_id: 详细信息

- [ ] 2.5 CLI: `repocraft logs <activity_id> [--follow]`
  - 读 DB logs
  - --follow: poll 1s, Ctrl-C 退出

- [ ] 2.6 并发验证
  - 3 个不同 repo issue → 并行处理
  - 同 repo 2 个 issue → 串行处理

### Milestone 3: Session 续接 + PR Review

- [ ] 3.1 respond_review Activity Kind
  - 查找原 fix activity 的 session_id
  - `claude --resume {session_id} -p "review comments: ..."`
  - resume 失败 → fallback 新 session

- [ ] 3.2 CLI: `repocraft review <pr_url>`
  - 快捷方式: submit --kind respond_review
  - 自动 fetch review comments (gh api)

- [ ] 3.3 Session ID 持久化
  - 从 stream-json 最后一条消息中提取 session_id
  - 存入 activities.session_id

### Milestone 4: 自动触发 — Watch + 主动扫描 + @Mention

- [ ] 4.1 repos 表增加 watch, last_event_at, scan_interval 字段
  - `repocraft watch <repo_url>` — 启动监听 + 定期扫描
  - `repocraft unwatch <repo_url>`
  - scan_interval 默认 "weekly", 可选 "daily" / "off"

- [ ] 4.2 Scheduler: GitHub event polling
  - 每 60s poll watched repos
  - GET /repos/{owner}/{repo}/events (If-None-Match)
  - 检测: IssuesEvent(opened), PullRequestReviewEvent
  - 过滤: label "repocraft" 或 "bug" (可配)
  - 去重: 同 trigger 不重复创建 activity

- [ ] 4.3 Scheduler: @mention 检测
  - Poll issue/PR comments for "@repocraft" (或配置的 bot name)
  - 检测到 @mention → 创建 task activity, prompt = comment 内容
  - 例: 用户在 issue 中评论 "@repocraft 帮我修一下这个"
  - 例: 用户在 PR 中评论 "@repocraft 加个单元测试"

- [ ] 4.4 Scheduler: 定期主动扫描
  - 根据 scan_interval, 定期为 watched repos 创建 scan activity
  - Scan prompt 让 agent 全面审查:
    - 安全漏洞 (依赖 CVE, 硬编码 secrets, SQL 注入等)
    - 过时依赖 (major version behind)
    - 测试覆盖缺口
    - 代码异味 / 明显 bug
    - 文档缺失
  - Agent 为每个发现: 创建 GitHub issue 或直接修复+PR
  - 避免重复: agent 应先搜索已有 issue 再创建新的

- [ ] 4.5 自动 triage
  - 新 issue → triage activity
  - Agent 评估 → 回复评论 + 打 label
  - 可修复 → 自动创建 fix_issue activity

### Milestone 5: 富媒体输出

- [ ] 5.1 容器内安装 Playwright + Chromium
  - 更新 Dockerfile (fat 镜像变体)

- [ ] 5.2 用户级 CLAUDE.md 增加浏览器指令
  - "UI 修复时, 用 playwright 截图, 附到 PR"
  - "截图保存到 /output/{repo_id}/"

- [ ] 5.3 Live preview
  - 容器内安装 cloudflared
  - 容器端口映射
  - Agent 启动 dev server + tunnel
  - `repocraft status` 显示 preview URL

- [ ] 5.4 PR 附带产物
  - Agent 在 PR description 中嵌入截图
  - 测试输出作为 comment

### Milestone 6: 稳定性

- [ ] 6.1 容器自愈 (dispatch 前 inspect, 不健康 → restart)
- [ ] 6.2 `repocraft retry <activity_id>`
- [ ] 6.3 `repocraft cleanup [--older-than 7d]`
- [ ] 6.4 `repocraft cost [--repo X] [--period 30d]`
- [ ] 6.5 Notification (macOS notification / webhook)

---

## File Structure (target)

```
src/repocraft/
├── cli.py                      # fix, submit, ask, daemon, status, logs, review, watch
├── config.py                   # 常量 + 环境变量读取
├── store.py                    # SQLite CRUD
├── scheduler.py                # 主循环 + worker pool + event poll + scan scheduling
├── dispatcher.py               # claude -p 执行 + 日志流
├── container/
│   ├── manager.py              # Docker 生命周期 + exec
│   └── Dockerfile              # repocraft-worker 镜像
├── github/
│   └── issue_fetcher.py        # 复用现有
└── templates/
    ├── user_claude_md.py       # 用户级 CLAUDE.md (通用规则)
    └── init_prompt.py          # repo init 的 prompt
```

~1000 行新代码, 7 个核心文件。

---

## Reuse / Delete / Create

| 现有文件 | 处理 |
|----------|------|
| github/issue_fetcher.py | 复用 |
| config.py | 简化重写 |
| container/manager.py | 重写 |
| container/image_builder.py | 替换为 Dockerfile |
| cli.py | 重写 |
| agent/* | 删除 (Claude Code 替代) |
| tools/* | 删除 (Claude Code 自带) |
| evidence/* | 删除 (PR 替代) |

---

## Milestones

```
M0 基础设施    ████░░░░░░  容器镜像 + 管理器 + SQLite + 用户级 CLAUDE.md
M1 端到端      ████████░░  init + dispatcher + CLI fix + 验证
  → `repocraft fix <url>` 跑通: 探索 repo → 修 bug → 提 PR
M2 后台+指令   ██████░░░░  scheduler + daemon + submit + ask + status + logs
  → 提交任务/直接下指令, 后台自动处理
M3 PR review   ████░░░░░░  session resume + review 命令
M4 自主运维    ████████░░  watch + @mention + 定期 scan + triage
  → Agent 自己发现问题, 自己修, 自己提 PR
M5 富媒体      ██████░░░░  Playwright 截图/录屏 + live preview
M6 稳定性      ████░░░░░░  重试 + 清理 + 成本 + 通知
```
