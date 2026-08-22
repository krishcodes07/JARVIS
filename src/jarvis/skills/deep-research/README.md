# Deep Research Skill

> Conduct comprehensive, multi-step web research, in-depth topic investigation, and web page content analysis using local `web_search` and `read_url` tools, saving full detailed reports to a file while returning an executive summary in chat.

## Overview
The `deep-research` skill defines a systematic research methodology for investigating complex topics, academic concepts, market trends, or technical frameworks using built-in search and URL content extraction tools.

---

## When to Use
Use this skill when:
- The user requests deep research, thorough investigation, or analytical synthesis on a topic.
- Multi-faceted information gathering from web pages, technical articles, and documentation is needed.
- A long-form detailed research report needs to be persisted to a file with an executive summary provided in chat.

---

## Date
Don't research through any old dates etc. you know the current date so use that.

---

## Required Tools

To execute this skill, use the following tools:

- `web_search`: Search the public web for real-time information, technical articles, news, documentation, or answers (`web_search(query="...", max_results=5)`).
- `read_url`: Fetch full text content of target web pages and convert into clean, structured Markdown (`read_url(url="...", max_chars=30000)`).
- `write_file`: Persist the completed detailed research report to a file (`write_file(path="...", content="...")`).
- `get_schema`: Retrieve full parameter definitions for any tool when needed (`get_schema(tool_names=[...])`).

---

## Step-by-Step Execution Protocol

### Step 1: Query Decomposition & Sub-Questions
1. Break down the primary research request into 3–5 targeted sub-questions (e.g., Background/Context, Architecture & Core Concepts, Performance & Benchmarks, Trade-offs & Comparisons, Best Practices).
2. Formulate specific, high-signal search queries for each sub-question.

### Step 2: Information Gathering with Local Search & URL Reading
1. **Web Search**: Execute `web_search(query=...)` across key sub-topics to find authoritative sources, articles, docs, and news.
2. **Result Evaluation**: Inspect search result snippets and identify the most credible, high-value source URLs.
3. **In-Depth URL Reading**: Call `read_url(url=...)` on the top relevant URLs to extract full page markdown, detailed explanations, architecture details, empirical metrics, and primary citations.
4. **Recursive Exploration**: If key details or citations from a page warrant further investigation, perform follow-up `web_search` and `read_url` calls.

### Step 3: Synthesis & Verification
1. Cross-reference facts, metrics, and claims across multiple distinct sources.
2. Extract key statistics, architectural patterns, code examples, citations, and trade-offs.
3. Filter out promotional content, unverified claims, or outdated information.

### Step 4: Save Detailed Report to File
1. Assemble a full, long-form detailed research report in markdown format (including Title, Executive Summary, Background & Problem Statement, Detailed Section-by-Section Analysis, Data/Comparative Tables, Key Findings, and References with Source URLs).
2. Save the complete report into a file (e.g. `research_report.md` or a user-specified file path) using `write_file`.

### Step 5: Present Summary in Chat
1. In the chat response to the user, provide **ONLY** a concise executive summary highlighting the core findings and key takeaways.
2. Conclude the chat message with the exact statement:
   `"I have saved the detailed report on <file_path> file."`

---

## Expected Chat Response Format

```markdown
# Deep Research Summary: [Topic]

## Key Highlights
- Highlight 1: Core finding from research.
- Highlight 2: Key performance or architectural takeaway.
- Highlight 3: Notable insights extracted from primary sources.

I have saved the detailed report on research_report.md file.
```