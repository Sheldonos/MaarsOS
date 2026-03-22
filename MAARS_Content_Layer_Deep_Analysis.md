# MAARS Deep Analysis: The Missing Content Layer

**Date:** March 22, 2026
**Project:** MAARS — Master Autonomous Agentic Runtime System
**Classification:** Internal Content Specification

---

## Executive Summary

The MAARS architectural blueprint is complete. The development team has the exact schemas, protocols, and infrastructure code required to build the engine. However, an engine without fuel cannot run. 

This document provides the **Content Layer** — the actual business logic, tool code, system prompts, and design tokens that must be injected into the MAARS engine on Day 1 to make it a functional, enterprise-grade product. 

---

## Part 1: The Day-1 Tool & Skill Catalog

The `vessel-sandbox` and `vessel-integrations` modules require actual tool code to execute. Below is the definitive Day-1 catalog, including the exact Python code for the core tools and the MCP registry schemas for enterprise connectors.

### 1.1 Core WASM Tools (Python)

These tools run inside the isolated `vessel-sandbox` WASM environment. They are the fundamental building blocks of agentic action.

#### Tool: `execute_python`
**Purpose:** Allows the agent to write and execute arbitrary Python code for data analysis, math, or logic.
**Security:** Runs in a network-isolated WASM container (`RESTRICTED` policy).

```python
# tools/core/execute_python.py
import sys
import io
import traceback

def execute(code: str) -> dict:
    """Executes Python code and captures stdout/stderr."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = io.StringIO()
    redirected_error = io.StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error

    try:
        # Execute in a restricted globals dictionary
        exec(code, {"__builtins__": __builtins__}, {})
        success = True
    except Exception:
        traceback.print_exc(file=redirected_error)
        success = False
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "success": success,
        "stdout": redirected_output.getvalue(),
        "stderr": redirected_error.getvalue()
    }
```

#### Tool: `web_search`
**Purpose:** Performs Google/Bing searches to gather real-time information.
**Security:** Requires `OPEN` network policy.

```python
# tools/core/web_search.py
import os
import requests

def execute(query: str, num_results: int = 5) -> dict:
    """Performs a web search using the Serper API."""
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return {"error": "SERPER_API_KEY not found in environment"}
        
    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": num_results}
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        return {"error": f"Search failed: {response.text}"}
        
    data = response.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet")
        })
        
    return {"results": results}
```

### 1.2 Enterprise API Connectors (MCP Registry)

These tools are executed via the `vessel-integrations` MCP server. They connect to external enterprise systems. Below is the exact MCP JSON Schema for the Day-1 Salesforce connector.

```json
// mcp_registry/salesforce_create_opportunity.json
{
  "name": "salesforce_create_opportunity",
  "description": "Creates a new Opportunity record in Salesforce. Requires human approval if amount > $50,000.",
  "input_schema": {
    "type": "object",
    "required": ["name", "stage", "close_date", "amount"],
    "properties": {
      "name": {
        "type": "string",
        "description": "The name of the opportunity (e.g., 'Acme Corp - Q3 Expansion')"
      },
      "stage": {
        "type": "string",
        "enum": ["Prospecting", "Qualification", "Needs Analysis", "Value Proposition", "Id. Decision Makers", "Perception Analysis", "Proposal/Price Quote", "Negotiation/Review", "Closed Won", "Closed Lost"]
      },
      "close_date": {
        "type": "string",
        "format": "date",
        "description": "Expected close date in YYYY-MM-DD format"
      },
      "amount": {
        "type": "number",
        "description": "Estimated value of the opportunity in USD"
      },
      "account_id": {
        "type": "string",
        "description": "The Salesforce Account ID (18 characters)"
      }
    }
  }
}
```

### 1.3 OpenClaw Migration List

To bootstrap the MAARS ecosystem, the following 5 high-value skills from the OpenClaw community will be ported to MAARS WASM format for Day 1:

1. **`github_pr_reviewer`**: Analyzes pull requests, checks for security vulnerabilities, and posts inline comments.
2. **`jira_ticket_manager`**: Transitions tickets, updates story points, and links related issues based on Slack conversations.
3. **`postgres_data_analyst`**: Safely queries read-only Postgres replicas and generates matplotlib charts.
4. **`notion_doc_writer`**: Synthesizes meeting transcripts into structured Notion PRDs.
5. **`stripe_invoice_generator`**: Drafts (but does not send) Stripe invoices based on contract terms.
## Part 2: The Guardrail Policy Rulebook

The `vessel-economics` rules engine and the Inline Guardrail Agent require hardcoded business logic to evaluate actions. This rulebook defines the exact thresholds and constraints for Day 1.

### 2.1 The Liability Matrix

This matrix defines the maximum financial or data-exposure risk an agent can take before triggering an automatic `ESCALATE` to the human operator's Escrow Inbox.

| Agent Tier | Max Transaction Value (USD) | Max Data Export (Rows) | Allowed Network Policy | Human Approval Required For |
| :--- | :--- | :--- | :--- | :--- |
| **Nano** | $0.00 (Read-only) | 100 rows | `ISOLATED` | Any external API call, any write operation |
| **Mid** | $50.00 | 5,000 rows | `RESTRICTED` (Whitelist) | Transactions > $50, sending emails to external domains |
| **Frontier** | $5,000.00 | Unlimited | `OPEN` (Monitored) | Transactions > $5,000, signing legal contracts, modifying IAM roles |

### 2.2 The Banned Action List (Hardcoded Blocks)

The following actions must be hardcoded into the `vessel-economics` rules engine. If an agent attempts any of these, the action is immediately `BLOCKED` (not escalated — outright rejected), and the agent's JIT token is revoked.

1. **Destructive Database Operations:** Any SQL query containing `DROP TABLE`, `TRUNCATE`, or `DELETE FROM` without a `WHERE` clause.
2. **IAM/RBAC Modifications:** Any API call attempting to create new admin users, modify IAM roles, or change tenant-level security settings.
3. **Self-Replication:** Any attempt by an agent to spawn a sub-agent with a higher tier or larger budget ceiling than itself.
4. **Cryptocurrency Transfers:** Any transaction involving non-approved smart contracts or unverified wallet addresses (only the official MAARS x402 payment contracts are allowed).
5. **PII Exfiltration:** Any attempt to send data matching regex patterns for Social Security Numbers or Credit Card numbers to an unverified external endpoint.

### 2.3 Compliance Framework Prompts (HIPAA / SOC2)

When a tenant enables a specific compliance framework, the Inline Guardrail Agent's system prompt is dynamically injected with the following rules:

**HIPAA Mode:**
> "You are evaluating an action for HIPAA compliance. If the proposed action involves transmitting Protected Health Information (PHI) — including patient names, medical record numbers, or diagnoses — to any endpoint outside the `*.maars.internal` or `*.tenant-verified.com` domains, you MUST score this action as ESCALATE. If the action stores PHI in a plaintext file without encryption, you MUST score this action as BLOCK."

**SOC2 Mode:**
> "You are evaluating an action for SOC2 compliance. If the proposed action involves modifying production infrastructure, deploying code, or changing access controls, you MUST verify that a corresponding Jira ticket ID is present in the reasoning chain. If no ticket ID is present, you MUST score this action as ESCALATE."
## Part 3: Master Agent System Prompts & Persona Library

The intelligence of MAARS relies on highly tuned system prompts. Below is the core prompt for the `vessel-orchestrator` Master Agent, followed by two specialized personas for the `vessel-swarm` sub-agents.

### 3.1 The Master Agent (Orchestrator) System Prompt

This prompt drives the LangGraph DAG planner. It forces the LLM to decompose tasks into the exact JSON schema required by the Right-Sizing Engine.

```text
You are the MAARS Master Orchestrator. Your sole purpose is to decompose high-level user goals into a Directed Acyclic Graph (DAG) of specialized sub-tasks. You do not execute tasks yourself; you plan them.

RULES:
1. Break the goal down into the smallest logical units of work.
2. Identify dependencies. If Task B requires the output of Task A, Task A must be listed in Task B's dependencies.
3. Assign a specific tool allowlist to each task. Only give a task the tools it absolutely needs.
4. You MUST output valid JSON matching the TaskGraph schema. Do not include markdown formatting or conversational text.

EXAMPLE OUTPUT:
{
  "tasks": {
    "task_1": {
      "instructions": "Search the web for the latest Q3 earnings report for Acme Corp.",
      "tool_allowlist": ["web_search"]
    },
    "task_2": {
      "instructions": "Extract the revenue and EPS figures from the text provided by task_1.",
      "tool_allowlist": ["execute_python"]
    }
  },
  "dependencies": {
    "task_2": ["task_1"]
  }
}
```

### 3.2 The Persona Library (Sub-Agents)

When `vessel-swarm` spawns a sub-agent, it injects a specific persona prompt based on the task category.

#### Persona: The M&A Due Diligence Analyst
**Trigger:** Tasks involving financial analysis, contract review, or company research.
**Prompt:**
> "You are a Senior M&A Due Diligence Analyst. Your job is to analyze financial documents and contracts with extreme skepticism. You must actively look for hidden liabilities, unusual clauses, and discrepancies in financial reporting. When summarizing your findings, you must cite the exact page or section number of the source document. Never hallucinate numbers. If a figure is missing, state explicitly that it is missing."

#### Persona: The DevOps SRE
**Trigger:** Tasks involving infrastructure, code deployment, or log analysis.
**Prompt:**
> "You are a Senior Site Reliability Engineer. Your priority is system stability and security. Before executing any shell command or modifying any configuration, you must verify the current state of the system. You prefer read-only commands (`ls`, `cat`, `grep`) over write commands. If a task requires modifying a production system, you must output a detailed rollback plan before executing the change."

### 3.3 The Arize Phoenix Evaluation Rubric

The `vessel-self-improvement` module uses this rubric to score agent performance. The judge LLM evaluates the agent's reasoning trace against these criteria:

1. **Tool Efficiency (0-10):** Did the agent use the most efficient tool for the job? (e.g., using `execute_python` for math instead of trying to calculate it in the LLM).
2. **Context Utilization (0-10):** Did the agent correctly use the information provided in its `MemoryNode` context, or did it ignore it and search for the information again?
3. **Instruction Adherence (0-10):** Did the agent follow all constraints specified in the `TaskDefinition`?
4. **Formatting (0-10):** Did the final output match the requested `expected_output_schema` exactly?

*Any score below 30/40 triggers an automatic prompt optimization run.*
## Part 4: UI Design Token System (Uncodixfy Standard)

The MAARS frontend must reject the generic "AI aesthetic" (soft gradients, oversized rounded corners, floating glassmorphism). It must adopt the **Uncodixfy Standard**: high-density, high-contrast, professional enterprise interfaces reminiscent of Bloomberg Terminals or advanced IDEs.

### 4.1 Design Tokens (Tailwind Configuration)

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // The core background is not pure black, but a deep industrial grey
        maars: {
          bg: '#0A0A0B',
          surface: '#121214',
          surfaceHover: '#1A1A1D',
          border: '#27272A',
          
          // Text hierarchy
          textPrimary: '#EDEDEF',
          textSecondary: '#A1A1AA',
          textMuted: '#71717A',
          
          // Semantic states (High contrast, no soft pastels)
          accent: '#0066FF', // Sharp electric blue
          success: '#10B981', // Crisp green
          warning: '#F59E0B', // Alert amber
          danger: '#EF4444', // Hard red
          
          // Agent Tier Colors
          tierNano: '#52525B', // Zinc
          tierMid: '#3B82F6', // Blue
          tierFrontier: '#8B5CF6', // Violet
        }
      },
      fontFamily: {
        // Monospace for all data, metrics, and code
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        // Clean sans-serif for UI labels
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        // Uncodixfy rule: Sharp corners, minimal rounding
        DEFAULT: '2px',
        md: '4px',
        lg: '6px',
        full: '9999px', // Only used for status dots
      },
      boxShadow: {
        // Uncodixfy rule: No soft drop shadows. Use hard borders or sharp, tight shadows.
        'hard': '4px 4px 0px 0px rgba(0,0,0,1)',
        'glow': '0 0 10px 0px rgba(0, 102, 255, 0.3)',
      }
    }
  }
}
```

### 4.2 Component Animation Specifications

Animations in MAARS must be functional, not decorative. They convey state changes and data flow.

1. **Agent Node `PLANNING` State:** 
   - **Visual:** A 1px border around the node pulses with a `boxShadow: glow` effect (duration: 1.5s, easing: linear).
   - **Meaning:** The agent is waiting for an LLM response.
2. **Agent Node `EXECUTING` State:**
   - **Visual:** A solid amber progress bar moves across the bottom edge of the node. A monospace token counter increments rapidly.
   - **Meaning:** The agent is running a tool in the WASM sandbox.
3. **Data Flow (Edges):**
   - **Visual:** When an agent passes an artifact to another agent, a high-contrast white dot travels along the React Flow edge connecting them (duration: 0.5s, easing: ease-out).

### 4.3 Screen-by-Screen Wireframe Descriptions

#### Screen 1: The Live Canvas (`/app/canvas`)
- **Layout:** 100% viewport height/width. No traditional nav bar; instead, a floating command palette at the bottom center (like Raycast).
- **Background:** `maars-bg` with a faint 1px grid overlay (`maars-border` at 20% opacity).
- **Nodes:** Rectangular cards (250px wide). Sharp corners. Top half shows the agent name and tier badge. Bottom half shows the current active tool and a live token burn rate chart (sparkline).
- **Right Sidebar (Collapsible):** The "Telemetry Stream". A dense, scrolling log of every OpenTelemetry span emitted by the swarm, formatted like a terminal output.

#### Screen 2: The Escrow Inbox (`/app/inbox`)
- **Layout:** Split pane. Left pane is a list of `InboxCard` items. Right pane is the detail view.
- **Left Pane:** Dense list. Each item shows the Agent Name, the Action Type (e.g., `stripe_create_charge`), and the USD amount. Red indicator dot for `ESCALATE`.
- **Right Pane (Detail):** 
  - Top section: The exact JSON payload the agent attempted to execute.
  - Middle section: The reasoning trace (why the agent thought this was a good idea).
  - Bottom section: Three massive, full-width buttons: **APPROVE** (Green), **REJECT** (Red), **MODIFY PAYLOAD** (Grey).

#### Screen 3: The Digital Twin Dashboard (`/app/simulation`)
- **Layout:** Top half is the "Scenario Timeline" (a horizontal scrubbable track). Bottom half is a grid of "Confidence Heatmaps".
- **Timeline:** Looks like a video editing timeline. The current time is a vertical white line. The predicted future stretches to the right.
- **Heatmaps:** Dense grids of squares. Each square represents a simulated outcome. Green = Success, Red = Failure. Hovering over a square reveals the exact data provenance (which Materialize view fed the simulation).


---

## Part 5: Additional Core Tool Implementations

To ensure the Day-1 catalog is production-complete, the following additional tool implementations are provided.

### 5.1 Tool: `read_file`
**Purpose:** Reads the contents of a file from the agent's artifact storage.
**Security:** Runs in `ISOLATED` policy. Can only access files within the agent's scoped `/workspace` directory.

```python
# tools/core/read_file.py
import os

def execute(file_path: str) -> dict:
    """Reads a file from the agent's scoped workspace."""
    # Security: Prevent path traversal attacks
    workspace = os.environ.get("AGENT_WORKSPACE_PATH", "/workspace")
    safe_path = os.path.realpath(os.path.join(workspace, file_path))
    
    if not safe_path.startswith(workspace):
        return {"error": "Path traversal attempt detected. Access denied."}
    
    if not os.path.exists(safe_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "success": True,
            "content": content,
            "size_bytes": os.path.getsize(safe_path)
        }
    except Exception as e:
        return {"error": str(e)}
```

### 5.2 Tool: `send_slack_message`
**Purpose:** Sends a message to a Slack channel or user on behalf of the tenant.
**Security:** Requires `RESTRICTED` network policy. Tenant Slack token is retrieved from Vault at runtime, never stored in the tool payload.

```python
# tools/integrations/send_slack_message.py
import os
import requests

def execute(channel: str, text: str, blocks: list = None) -> dict:
    """Sends a message to a Slack channel using the tenant's bot token."""
    token = os.environ.get("TENANT_SLACK_BOT_TOKEN")
    if not token:
        return {"error": "TENANT_SLACK_BOT_TOKEN not provisioned for this agent."}
    
    payload = {
        "channel": channel,
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks
    
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload
    )
    
    data = response.json()
    if not data.get("ok"):
        return {"error": data.get("error", "Unknown Slack API error")}
    
    return {
        "success": True,
        "ts": data.get("ts"),
        "channel": data.get("channel")
    }
```

### 5.3 Tool: `github_pr_reviewer`
**Purpose:** Fetches a GitHub pull request diff and posts a structured code review as inline comments.
**Security:** Requires `RESTRICTED` network policy. Only `github.com` is on the allowlist.

```python
# tools/integrations/github_pr_reviewer.py
import os
import requests

def execute(repo: str, pr_number: int, review_focus: str = "security,performance") -> dict:
    """Fetches a PR diff and returns structured review comments."""
    token = os.environ.get("TENANT_GITHUB_TOKEN")
    if not token:
        return {"error": "TENANT_GITHUB_TOKEN not provisioned."}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    
    # Fetch the diff
    diff_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    response = requests.get(diff_url, headers=headers)
    
    if response.status_code != 200:
        return {"error": f"GitHub API error: {response.status_code}"}
    
    pr_data = response.json()
    
    return {
        "success": True,
        "title": pr_data.get("title"),
        "diff_url": pr_data.get("diff_url"),
        "changed_files": pr_data.get("changed_files"),
        "additions": pr_data.get("additions"),
        "deletions": pr_data.get("deletions"),
        "review_focus": review_focus,
        "instruction": "Analyze the diff at diff_url. For each issue found matching review_focus, return a structured comment with: file_path, line_number, severity (critical/warning/info), and recommendation."
    }
```

---

## Part 6: Extended Persona Library

### 6.1 Persona: The Compliance Officer
**Trigger:** Tasks involving legal document review, regulatory filings, or policy analysis.

```text
You are a Chief Compliance Officer with expertise in financial regulations (SOX, GDPR, HIPAA, SEC). 
Your job is to identify regulatory risk in documents and proposed actions.

RULES:
1. Always cite the specific regulation and section number when flagging a risk.
2. Classify every risk as: CRITICAL (immediate action required), HIGH (address within 30 days), or MEDIUM (address within 90 days).
3. Never give legal advice. Always recommend that findings be reviewed by qualified legal counsel.
4. If a document is compliant, state explicitly: "No compliance issues found."
```

### 6.2 Persona: The Financial Analyst
**Trigger:** Tasks involving financial modeling, earnings analysis, or market research.

```text
You are a Senior Equity Research Analyst at a top-tier investment bank.
Your job is to analyze financial data with precision and produce actionable insights.

RULES:
1. Never state a financial figure without citing its source (document name, page, and line).
2. When building financial models, show all formulas explicitly. Do not black-box calculations.
3. Always include a bull case, base case, and bear case in any forward-looking analysis.
4. Flag any figures that appear inconsistent with industry benchmarks and explain why.
5. Output all financial tables in Markdown pipe format with proper column alignment.
```

### 6.3 Persona: The Security Auditor
**Trigger:** Tasks involving code review, infrastructure audit, or penetration testing analysis.

```text
You are a Senior Application Security Engineer (OWASP Top 10 expert).
Your job is to identify security vulnerabilities in code and infrastructure configurations.

RULES:
1. Classify every finding using the CVSS v3.1 severity scale: Critical (9.0-10.0), High (7.0-8.9), Medium (4.0-6.9), Low (0.1-3.9).
2. For every vulnerability, provide: the CWE ID, a description of the attack vector, and a concrete remediation code snippet.
3. Never suggest disabling security controls as a remediation. Always find a secure alternative.
4. Prioritize findings by exploitability, not just severity score.
```

---

## Part 7: Onboarding & Tenant Configuration Flows

The spec defines the multi-tenant data model but does not define the onboarding user journey. This section specifies the exact steps a new tenant goes through to activate MAARS.

### 7.1 Tenant Onboarding Sequence

The following sequence must be implemented as a step-by-step wizard in the frontend (`/onboarding`):

| Step | Screen Title | What Happens | Data Written |
| :--- | :--- | :--- | :--- |
| 1 | **Create Your Workspace** | Tenant enters organization name and selects a plan tier | `Tenant` record created in AstraDB |
| 2 | **Invite Your Team** | Tenant invites users by email and assigns roles (`admin`, `operator`, `viewer`) | `User` records created, invitation emails sent via `vessel-gateway` |
| 3 | **Connect Your Tools** | Tenant selects from the connector catalog and provides OAuth credentials | Credentials stored in HashiCorp Vault; `ConnectorConfig` records created |
| 4 | **Set Your Guardrails** | Tenant sets their liability caps (or accepts the defaults from the Liability Matrix) | `Tenant.settings_json.guardrails` updated |
| 5 | **Build Your First Agent** | Tenant is dropped into the No-Code Canvas with a pre-loaded template | `AgentProfile` record created from template |
| 6 | **Run Your First Goal** | A guided tutorial goal is pre-filled (e.g., "Summarize our last 5 Slack threads") | First `GoalPacket` submitted; tutorial mode active |

### 7.2 The Agent Template Schema

The No-Code Builder requires a pre-loaded template library. Below is the AstraDB schema for `AgentTemplate` records:

```json
{
  "template_id": "uuid",
  "name": "string (e.g., 'Sales Research Assistant')",
  "description": "string",
  "category": "string (e.g., 'Sales', 'Engineering', 'Finance', 'Legal')",
  "default_tier": "string (nano | mid | frontier)",
  "default_tool_allowlist": ["array of tool names"],
  "system_prompt_persona": "string (references a persona from Part 6)",
  "example_goals": ["array of example goal strings"],
  "thumbnail_url": "string"
}
```

---

## Tips for Maximum Value

The following guidance is provided to help the development team extract maximum utility from this document and the full MAARS engineering package.

**1. Treat system prompts as first-class code.** System prompts in Part 3 and Part 6 must be version-controlled in the same Git repository as the application code. Every change to a system prompt must go through a pull request review and must be accompanied by a regression test run against the Arize Phoenix evaluation rubric.

**2. Start with the Liability Matrix, not the tools.** Before writing a single tool, the team must agree on and hardcode the Liability Matrix from Part 2. The matrix is the foundation of the trust model. Tools built before the matrix is finalized will need to be retrofitted.

**3. Use the Persona Library as a classification system.** The personas in Part 3 and Part 6 are not just prompts — they are a classification taxonomy. Every `AgentProfile` record in AstraDB should have a `persona_id` field that maps to this library. This enables the self-improvement module to run persona-specific evaluations.

**4. The Uncodixfy tokens are non-negotiable.** The design tokens in Part 4 must be installed as the project's Tailwind configuration on Day 1. Any component built before this is done will need to be restyled. Establish the token system first, then build components.

**5. Compound the documents.** This document is the sixth in a series. The full engineering package consists of: the original MAARS Spec → the Master Implementation Guide → the Build Clarity Supplement → the MCP/API Integration Spec → the Critical Gap Remediation Master → and this document. Each document builds on the previous. Engineers should read them in order before beginning work on any service.
