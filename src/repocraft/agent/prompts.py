from __future__ import annotations

from ..github.issue_fetcher import GitHubIssue

SYSTEM_PROMPT = """\
You are RepoCraft, an expert software engineer agent. Your job is to reproduce, fix, and verify bugs in GitHub repositories.

You operate inside a Docker container where the repository has been cloned to /workspace/repo.

Available tools:
- container_exec: Run shell commands in the container (working dir: /workspace/repo)
- container_read: Read file contents from the container
- container_write: Write file contents to the container
- container_list_files: List files in a directory (max depth 3)
- capture_evidence: Record important findings, outputs, and conclusions

Rules:
- Always use capture_evidence to record significant findings
- Be methodical: explore first, then act
- Keep changes minimal and focused on the specific bug
- Every conclusion must be backed by evidence
"""


def build_base_context(issue: GitHubIssue) -> str:
    parts = [
        f"# GitHub Issue #{issue.number}: {issue.title}",
        f"**URL:** {issue.url}",
        f"**State:** {issue.state}",
        f"**Author:** {issue.author}",
    ]
    if issue.labels:
        parts.append(f"**Labels:** {', '.join(issue.labels)}")
    parts.append(f"\n## Issue Description\n\n{issue.body or '(no description)'}")
    if issue.comments:
        parts.append("\n## Comments\n")
        for i, comment in enumerate(issue.comments[:5], 1):
            parts.append(f"### Comment {i}\n{comment}")
    return "\n".join(parts)


REPRODUCE_PROMPT_TEMPLATE = """\
{issue_context}

---

## Your Task: REPRODUCE THE BUG

You are in Phase 1: Reproduction. Your goal is to confirm that the bug described in the issue actually exists in this repository.

**Steps to follow:**
1. Explore the repository structure to understand the codebase (container_list_files, container_read key files)
2. Understand what the issue is about and where the bug likely lives
3. Set up the environment: install dependencies using the appropriate package manager
4. Write and run a minimal test case or command that triggers the bug
5. Capture ALL relevant evidence using capture_evidence:
   - Use evidence_type "command_output" for command results
   - Use evidence_type "error_output" for error messages/tracebacks
   - Use evidence_type "observation" for code analysis
   - Use evidence_type "conclusion" for your final verdict
6. End your response with exactly one line: either "REPRODUCED: YES" or "REPRODUCED: NO"

**Important:** The reproduction must be concrete. Show the actual error, traceback, or wrong output. Do not assume — verify.
"""

FIX_PROMPT_TEMPLATE = """\
{issue_context}

---

## Reproduction Evidence (from Phase 1)

{reproduction_evidence}

---

## Your Task: FIX THE BUG

You are in Phase 2: Fix. The bug has been confirmed reproduced. Now apply the minimal fix.

**Steps to follow:**
1. Review the reproduction evidence carefully to understand the root cause
2. Locate the exact code that needs to change (use container_read)
3. Apply the minimal fix using container_write — change only what is necessary
4. Capture evidence for each change using capture_evidence:
   - Use evidence_type "observation" for root cause analysis
   - Use evidence_type "file_content" for the changed code
   - Use evidence_type "conclusion" for why this fix addresses the root cause
5. End your response with exactly one line: either "FIXED: YES" or "FIXED: NO"

**Important:** Do NOT run tests yet — that is Phase 3's job. Focus only on making the minimal correct fix.
"""

VERIFY_PROMPT_TEMPLATE = """\
{issue_context}

---

## Reproduction Evidence (from Phase 1)

{reproduction_evidence}

---

## Fix Evidence (from Phase 2)

{fix_evidence}

---

## Your Task: VERIFY THE FIX

You are in Phase 3: Verification. Re-run the reproduction scenario and the test suite to confirm the fix works.

**Steps to follow:**
1. Re-run the exact same command/test that triggered the bug in Phase 1
2. Run the full test suite if one exists (pytest, npm test, etc.)
3. Get the git diff to show all changes made: container_exec with "git diff HEAD"
4. Capture ALL results using capture_evidence:
   - Use evidence_type "test_result" for test suite output
   - Use evidence_type "command_output" for reproduction command output
   - Use evidence_type "diff" for the git diff output
   - Use evidence_type "conclusion" for your final verdict
5. End your response with exactly one line: either "VERIFIED: YES" or "VERIFIED: NO"

**Important:** VERIFIED: YES only if the original bug is gone AND no new test failures were introduced.
"""


def build_reproduce_prompt(issue: GitHubIssue) -> str:
    return REPRODUCE_PROMPT_TEMPLATE.format(issue_context=build_base_context(issue))


def build_fix_prompt(issue: GitHubIssue, reproduction_evidence: str) -> str:
    return FIX_PROMPT_TEMPLATE.format(
        issue_context=build_base_context(issue),
        reproduction_evidence=reproduction_evidence,
    )


def build_verify_prompt(
    issue: GitHubIssue,
    reproduction_evidence: str,
    fix_evidence: str,
) -> str:
    return VERIFY_PROMPT_TEMPLATE.format(
        issue_context=build_base_context(issue),
        reproduction_evidence=reproduction_evidence,
        fix_evidence=fix_evidence,
    )
