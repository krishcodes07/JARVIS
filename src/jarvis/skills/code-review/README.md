# Code Review Skill

> Perform a rigorous, multi-dimensional code audit covering architecture, security, performance, maintainability, type safety, and test coverage.

## Overview
The `code-review` skill defines a systematic workflow for auditing codebases, pull requests, or individual source files. It ensures that code modifications adhere to professional software engineering standards, security best practices, and project conventions.

---

## When to Use
Use this skill when:
- Reviewing new code or modified files prior to merging or release.
- Conducting security audits or refactoring existing modules.
- Evaluated codebase health, design patterns, and adherence to clean code principles.

---

## Required & Recommended Tools
- `read_file` (to inspect target code files)
- `list_directory` (to discover project file hierarchy)
- `run_command` (to execute linters, type checkers like `mypy`/`ruff`, or test suites)

---

## Step-by-Step Execution Protocol

### Step 1: Context & Scope Gathering
1. Identify target files, modules, or git diffs to review.
2. Read the source code along with relevant interfaces, imported dependencies, and existing tests.
3. Verify the intended functionality and acceptance criteria.

### Step 2: Automated Analysis & Lint Check
1. Execute project linters and static analyzers (e.g. `ruff check`, `mypy`, `eslint`, or `pytest`) if accessible via shell tools.
2. Record all automated warnings, type errors, or syntax issues.

### Step 3: Manual Code Inspection Dimensions
Inspect the target code across six critical dimensions:
1. **Correctness & Logic**: Boundary conditions, edge cases, off-by-one errors, null checks, race conditions.
2. **Security**: OWASP top vulnerabilities, unvalidated input, credential exposure, unsafe shell executions.
3. **Performance & Scalability**: Time/space complexity, resource leaks, N+1 query problems, blocking I/O on async loops.
4. **Architecture & Design**: Single Responsibility, DRY principle, component boundaries, modularity, schema consistency.
5. **Readability & Maintainability**: Naming clarity, function size, dead code, unnecessary complexity, inline documentation.
6. **Error Handling & Resilience**: Graceful error degradation, explicit exception catching, context retention in logs.

### Step 4: Constructing Review Findings
Categorize findings using severity levels:
- 🔴 **Critical**: Vulnerabilities, data corruption risks, runtime crashes (must fix).
- 🟡 **Warning**: Suboptimal patterns, performance issues, missing error handling (should fix).
- 🔵 **Suggestion**: Refactoring opportunities, naming improvements, style tweaks (optional).
- 🟢 **Positive**: Exemplary patterns or well-designed abstractions worth acknowledging.

### Step 5: Generating the Review Report
Format the review into a structured markdown report with code diffs and concrete fix recommendations:

```markdown
# Code Review Summary

## Overview
Brief evaluation of the pull request or file changes.

## Findings & Recommendations

### 🔴 Critical Issues
- **[File Name:Line Number]**: Issue description.
  ```python
  # Suggested fix
  ```

### 🟡 Warnings
- **[File Name:Line Number]**: Issue description.

### 🔵 Suggestions & Refactoring
- **[File Name:Line Number]**: Recommendation.

## Summary Checklist
- [ ] Security verified
- [ ] Unit tests present & passing
- [ ] No performance regressions
```
