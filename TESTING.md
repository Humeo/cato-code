# RepoCraft v2 - 快速测试指南

## 前提条件

✅ Docker 镜像已构建: `repocraft-worker:v1` (645MB)
✅ 环境变量已设置:

**标准 Anthropic API**:
```bash
export ANTHROPIC_API_KEY="sk-ant-xxx"
export GITHUB_TOKEN="ghp_xxx"
```

**或使用自定义 API 端点**（如代理服务）:
```bash
export ANTHROPIC_AUTH_TOKEN="sk-xxx"
export ANTHROPIC_BASE_URL="https://cc.580ai.ne"
export GITHUB_TOKEN="ghp_xxx"
```

## 测试命令

### 1. 基础测试（小型 issue）

```bash
# 找一个简单的 bug issue 测试
uv run repocraft fix https://github.com/owner/repo/issues/123
```

**预期行为**:
1. 显示 "RepoCraft v2" 面板
2. 注册 repo 到数据库
3. 创建 activity
4. 启动容器（如果未运行）
5. 克隆仓库（如果不存在）
6. 运行 init activity（首次）- 生成 CLAUDE.md
7. 运行 fix_issue activity
8. 实时显示日志
9. 最终显示成功/失败面板

### 2. 检查数据库

```bash
sqlite3 ~/.repocraft/repocraft.db "SELECT id, repo_id, kind, status FROM activities ORDER BY created_at DESC LIMIT 5;"
```

### 3. 查看日志

```bash
sqlite3 ~/.repocraft/repocraft.db "SELECT line FROM logs WHERE activity_id='<activity-id>' LIMIT 20;"
```

### 4. 检查容器状态

```bash
docker ps | grep repocraft-worker
docker exec repocraft-worker ls -la /repos/
```

### 5. 检查生成的 CLAUDE.md

```bash
docker exec repocraft-worker cat /repos/owner-repo/CLAUDE.md
```

## 常见问题

### Q: 程序卡住不动
**A**: 检查是否在构建镜像（首次运行需要 5-10 分钟）
```bash
docker images | grep repocraft-worker
```

### Q: "Container not running" 错误
**A**: 手动启动容器
```bash
docker start repocraft-worker
# 或删除旧容器重新创建
docker rm -f repocraft-worker
```

### Q: Git clone 失败
**A**: 检查 GITHUB_TOKEN 是否设置
```bash
echo $GITHUB_TOKEN
docker exec repocraft-worker env | grep GITHUB_TOKEN
```

### Q: Claude API 错误
**A**: 检查 API key 和 base URL
```bash
# 标准 API
echo $ANTHROPIC_API_KEY
docker exec repocraft-worker env | grep ANTHROPIC_API_KEY

# 自定义端点
echo $ANTHROPIC_AUTH_TOKEN
echo $ANTHROPIC_BASE_URL
docker exec repocraft-worker env | grep ANTHROPIC
```

## 调试模式

```bash
# 启用详细日志
uv run repocraft fix <issue_url> --verbose

# 查看容器日志
docker logs repocraft-worker

# 进入容器调试
docker exec -it repocraft-worker bash
cd /repos/owner-repo
git status
claude --version
gh --version
```

## 预期输出示例

```
╭─────────────────────────────────────────────────── Starting ───────────────────────────────────────────────────╮
│ RepoCraft v2                                                                                                   │
│ Repo: owner/repo                                                                                               │
│ Issue: #123                                                                                                    │
│ Model: claude-sonnet-4-6                                                                                       │
│ Max turns: 200                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Registered repo: owner-repo
Created activity: 7ad8fbba-ecef-4a0e-afa9-805178d617d4

▶ Dispatching activity...
INFO: Building image repocraft-worker:v1 (this may take 5-10 minutes on first run)...
INFO: BUILD: Step 1/8 : FROM ubuntu:24.04
INFO: BUILD: Step 2/8 : RUN apt-get update...
...
INFO: Container repocraft-worker started
INFO: Cloned https://github.com/owner/repo -> /repos/owner-repo
INFO: Repo owner-repo needs init, running init activity first
INFO: Init activity completed
INFO: Reset /repos/owner-repo to origin/main
INFO: Executing: cd /repos/owner-repo && claude -p "..." --output-format stream-json...
[实时日志流...]
INFO: Claude command completed with exit code 0 (1234 lines logged)

╭─────────────────────────────────────────────────── Activity Completed ─────────────────────────────────────────╮
│ SUCCESS                                                                                                        │
│                                                                                                                │
│ Fixed issue #123 and created PR #456                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## 下一步

M1 完成后，M2 将添加：
- `repocraft daemon` - 后台调度器
- `repocraft submit <issue_url>` - 异步队列
- `repocraft ask <repo> "<instruction>"` - 自由指令
- `repocraft status` - 查看进度
- `repocraft logs <activity_id> --follow` - 实时日志
