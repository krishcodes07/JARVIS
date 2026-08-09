# Bug Hunting Skill

> Investigate, isolate, reproduce, and fix software defects using empirical log analysis, step-by-step trace reproduction, and regression verification.

## Overview
The `bug-hunting` skill guides the AI agent through a methodical process of diagnosing runtime errors, unhandled exceptions, unexpected behavior, and flaky test failures. It enforces strict empirical evidence collection over guessing.

---

## When to Use
Use this skill when:
- Investigating runtime crashes, failed unit tests, or unexpected output.
- Debugging complex multi-component interactions, async race conditions, or memory leaks.
- Performing root-cause analysis on reported bugs.

---

## Required & Recommended Tools
- `read_file` (to inspect logs, stack traces, and source code)
- `run_command` (to execute test runners, capture debug outputs, or run diagnostic scripts)
- `edit_file` (to apply fixes or inject temporary debug logs)

---

## Step-by-Step Execution Protocol

### Step 1: Log & Traceback Inspection (Mandatory First Step)
1. Never guess the root cause without examining raw tracebacks or log outputs.
2. Read complete, un-truncated error logs, exception messages, and line numbers.
3. Identify exact failure location, input parameters, and environment state.

### Step 2: Minimal Reproduction Setup
1. Formulate a hypothesis explaining why the error occurred.
2. Create a minimal reproduction script or isolate the exact unit test that fails.
3. Run the reproduction step to confirm the issue is consistently reproducible.

### Step 3: Upstream & Downstream Trace Analysis
1. Trace input parameters backward from the point of failure to the data source.
2. Check for missing validation, null dereferences, invalid type coercion, or unexpected API payload mutations.
3. Verify if similar invocations in other parts of the codebase could suffer from the same defect.

### Step 4: Defensive Fix Implementation
1. Develop a minimal, target fix addressing the underlying root cause (do not mask symptoms or swallow exceptions).
2. Ensure exception handling retains error context and provides clear log messaging.
3. Add defensive assertions or input validation where appropriate.

### Step 5: Verification & Regression Testing
1. Run the reproduction script/test to verify the bug is resolved.
2. Run the full test suite to guarantee no unexpected regressions were introduced.
3. Summarize the root cause, fix rationale, and verification results for the user.

---

## Standard Bug Report Schema
```markdown
# Bug Investigation & Resolution Report

## 1. Issue Summary
- **Symptom**: Brief description of the observed defect.
- **Root Cause**: Explanation of why the code failed.

## 2. Evidence & Log Analysis
```
Exact error log snippet or traceback
```

## 3. Solution Applied
- Description of code modifications.
- [Filename & Line Range](file:///path/to/file#L10-L25) updated.

## 4. Verification Results
- [x] Minimal reproduction test passes.
- [x] Full test suite green.
```
