# Deep Research Skill

> Conduct comprehensive, multi-step web research, scientific paper analysis, and web scraping using official Firecrawl MCP tools, saving full detailed reports to a file while returning an executive summary in chat.

## Overview
The `deep-research` skill defines a systematic research methodology for investigating complex topics, academic concepts, market trends, or technical frameworks using Firecrawl MCP tools.

---

## When to Use
Use this skill when:
- The user requests deep research, thorough investigation, or analytical synthesis on a topic.
- Multi-faceted information gathering from web pages and scientific papers is needed.
- A long-form detailed research report needs to be persisted to a file with an executive summary provided in chat.

---

## Date
Don't research through any old dates etc. you know the current date so use that.

## Required Tools

To execute this skill, use the following tools (use `get_schema` to retrieve the JSON parameters schema for any tool before invocation):

- `firecrawl-mcp__firecrawl_search`: Search web, news, GitHub, or research papers.
- `firecrawl-mcp__firecrawl_scrape`: Scrape and extract content from specific web URLs into clean markdown.
- `firecrawl-mcp__firecrawl_research_search_papers`: Search research paper metadata and abstracts across scientific corpora.
- `firecrawl-mcp__firecrawl_research_read_paper`: Retrieve in-body passages from target research papers.
- `get_schema`: Retrieve full parameter definitions for any tool when needed (`get_schema(tool_names=[...])`).
- `write_file`: Persist the completed detailed research report to a file.

---

## Step-by-Step Execution Protocol

### Step 1: Query Decomposition & Sub-Questions
1. Break down the primary research request into 3–5 targeted sub-questions (e.g. Architecture, Performance Benchmarks, Trade-offs, Academic Findings).
2. Formulate targeted search queries for each sub-question.

### Step 2: Schema Inspection & Information Gathering
1. If parameter schemas are needed, then call get_schema
2. **Web Search**: Call `firecrawl-mcp__firecrawl_search` for web context, technical articles, or code repositories.
3. **Page Scraping**: Call `firecrawl-mcp__firecrawl_scrape(url=...)` on top search results to extract full page markdown.
4. **Academic/Paper Search**: Call `firecrawl-mcp__firecrawl_research_search_papers(query=...)` to discover relevant scientific papers and preprints.
5. **Paper In-Depth Reading**: Call `firecrawl-mcp__firecrawl_research_read_paper(paperId=..., question=...)` to extract relevant passages from target papers.

### Step 3: Synthesis & Verification
1. Cross-reference data across web sources and research papers.
2. Extract key metrics, citations, code examples, and trade-offs.
3. Filter out redundant or unverified information.

### Step 4: Save Detailed Report to File
1. Assemble a full, long-form detailed research report in markdown format (including Executive Summary, Background, Technical Analysis, Research Paper Passages & Citations, Comparative Tables, and References).
2. Save the complete report into a file (e.g. `research_report.md` or user-specified file path) using `write_file`.

### Step 5: Present Summary in Chat
1. In the chat response to the user, provide **ONLY** a concise executive summary highlighting key findings.
2. Conclude the chat message with the exact statement:
   `"I have saved the detailed report on <file_path> file."`

---

## Expected Chat Response Format

```markdown
# Deep Research Summary: [Topic]

## Key Highlights
- Highlight 1: Core finding from research.
- Highlight 2: Key performance or architectural takeaway.
- Highlight 3: Passages extracted from research papers.

I have saved the detailed report on research_report.md file.
```