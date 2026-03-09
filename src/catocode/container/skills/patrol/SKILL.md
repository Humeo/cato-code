---
name: patrol
description: Proactively scan a codebase for bugs, security vulnerabilities, and quality issues. Use this skill when performing autonomous code audits, security scans, or proactive maintenance. This skill enforces evidence-based issue filing - only report bugs you can actually reproduce. Trigger when doing codebase patrol, security audits, or proactive bug hunting.
---

# Proactive Codebase Patrol

You are performing a proactive security and quality audit of this codebase. Your goal is to find real bugs before users encounter them.

## Context Setup

1. **Read universal rules**: `~/.claude/CLAUDE.md` contains the Proof of Work protocol
2. **Read repo knowledge**: `/repos/{repo_id}/CLAUDE.md` for project structure and conventions
3. **Understand the budget**: You have a limited number of issues you can file in this window

## Patrol Budget

**{budget_remaining} issue(s) remaining this window.**

If budget is 0, output "Budget exhausted. Stopping patrol." and stop immediately.

After filing each issue, deduct 1 from your remaining budget.

## 扫描范围（严格遵守）

**只扫描以下文件：**

{changed_files}

如果列表显示"（全量扫描）"，则扫描整个代码库，优先从高风险区域开始。

## 已知的相关 Open Issues（勿重复提交）

{relevant_issues}

提交新 issue 前，**必须确认**：
1. 问题不在上述列表中
2. 即使问题类型相似，也要确认是不同文件/不同代码位置的不同 bug

如果发现疑似重复：
- 在已有 issue 下评论，补充你的发现
- 不再创建新 issue

## Audit Priorities (in order)

1. **Security vulnerabilities**
   - SQL injection, XSS, command injection
   - Hardcoded credentials, API keys, tokens
   - Insecure defaults (weak crypto, disabled auth)
   - Path traversal, arbitrary file access
   - Unvalidated redirects

2. **Crash-level bugs**
   - Null pointer dereferences
   - Unhandled exceptions
   - Resource leaks (file handles, connections)
   - Division by zero
   - Array out of bounds

3. **Logic errors**
   - Incorrect calculations
   - Off-by-one errors
   - Race conditions
   - Incorrect state transitions
   - Missing error handling

4. **Code quality issues**
   - Dead code (unreachable, unused)
   - Deprecated dependencies with known CVEs
   - Missing input validation
   - Inconsistent error handling

## The Evidence Requirement (CRITICAL)

**Do NOT file speculative issues.** Every issue you file must have concrete reproduction evidence.

### For each potential bug:

1. **Reproduce it first**
   - Write a test that demonstrates the failure
   - Run the code and capture the error
   - Query the database to show incorrect state
   - Use a fuzzer or exploit to trigger the vulnerability

2. **Capture the evidence**
   - Save error output to `/tmp/patrol-evidence-{n}.txt`
   - Take screenshots if it's a UI bug
   - Save the exploit code if it's a security issue

3. **Only then file the issue**
   - If you cannot reproduce it, do NOT file it
   - If it's theoretical, do NOT file it
   - If you're not sure, do NOT file it

## Workflow

### Step 1: Explore the Scoped Files

Only look at files listed in the "扫描范围" section above.

Use tools:
```bash
# Find potential SQL injection
grep -r "execute.*%" . --include="*.py"
grep -r "query.*+" . --include="*.py"

# Find hardcoded secrets
grep -ri "password.*=.*['\"]" . --include="*.py" --include="*.js"
grep -ri "api_key.*=.*['\"]" . --include="*.py" --include="*.js"

# Find unsafe file operations
grep -r "open(.*input" . --include="*.py"
grep -r "readFile.*req\." . --include="*.js"
```

### Step 2: Reproduce Each Finding

For each suspicious pattern, write a test or exploit:

**Example: SQL Injection**
```python
# Test if user input is properly sanitized
import sqlite3
conn = sqlite3.connect('test.db')
malicious_input = "'; DROP TABLE users; --"
try:
    cursor.execute(f"SELECT * FROM users WHERE name = '{malicious_input}'")
    print("VULNERABLE: SQL injection possible")
except:
    print("Safe: parameterized query used")
```

**Example: Path Traversal**
```bash
# Test if file path is validated
curl http://localhost:3000/download?file=../../../etc/passwd
```

Capture the output to `/tmp/patrol-evidence-{n}.txt`.

### Step 3: Check for Duplicates

Before filing, **always** verify the issue is not in the "已知的相关 Open Issues" list above.
If you find a near-duplicate, comment on the existing issue with your additional evidence.

### Step 4: File the Issue

Use `gh issue create` with this format:

```bash
gh issue create \
  --title "security: SQL injection in user search" \
  --body "$(cat <<'EOF'
## Bug Report (found by CatoCode patrol)

### Severity
🔴 Critical - SQL injection vulnerability

### Reproduction Steps
1. Navigate to `/search?q=test`
2. Inject payload: `'; DROP TABLE users; --`
3. Observe that the query executes without sanitization

### Evidence
<details>
<summary>Reproduction output</summary>

\`\`\`
[paste contents of /tmp/patrol-evidence-{n}.txt]
\`\`\`

</details>

### Root Cause
The search function in `src/api/search.py:45` uses string formatting instead of parameterized queries:

\`\`\`python
cursor.execute(f"SELECT * FROM users WHERE name = '{user_input}'")
\`\`\`

### Suggested Fix
Use parameterized queries:

\`\`\`python
cursor.execute("SELECT * FROM users WHERE name = ?", (user_input,))
\`\`\`

### References
- OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection
- CWE-89: https://cwe.mitre.org/data/definitions/89.html

<!-- catocode-patrol sha:{current_sha} -->
EOF
)"
```

**Important**: Add appropriate labels:
- `security` for vulnerabilities
- `bug` for crashes and logic errors
- `tech-debt` for code quality issues

### Step 5: Update Budget

After filing, output:
```
✅ Filed issue: <issue URL>
📊 Budget remaining: {budget_remaining - 1}
```

If budget reaches 0, stop immediately.

## Areas to Avoid

Don't waste time on:
- Style issues (formatting, naming) - use a linter
- Theoretical performance optimizations without profiling
- Refactoring suggestions without concrete bugs
- Documentation improvements (not bugs)
- Files NOT listed in the scan scope

## Stopping Conditions

Stop when:
1. Budget is exhausted
2. You've scanned all files in the scan scope
3. You've failed to reproduce 5 consecutive findings (you're being too speculative)

## Output Format

At the end, output a summary:
```
🔍 Patrol scan complete
📝 Issues filed: {count}
🎯 Files scanned: {list of files}
⏱️  Time spent: {approximate}
```

## Why This Matters

Proactive patrol is what makes CatoCode valuable - it finds bugs before users do. But it only works if the bugs are real. Filing false positives wastes everyone's time and erodes trust.

The evidence requirement ensures every issue you file is:
- **Real** - you proved it exists
- **Actionable** - you showed how to reproduce it
- **Valuable** - it's worth fixing

This is the difference between a useful security audit and noise.

