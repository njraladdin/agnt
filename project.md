# agnt: infrastructure for agency

**The principle for CORE capacility vs AGENT-SPECIFIC capability:**

Ask: "Would 80%+ of agents benefit from this, regardless of domain?"

```
Core engine (agnt):              Agent-specific:
─────────────────────────────    ─────────────────────────────
Memory / state persistence       Scraping patterns
Document ingestion               E-commerce extraction logic
Code execution                   Form-filling workflows
Browser access                   Research synthesis prompts
Tool calling framework           Domain-specific tools
Subagent orchestration
LLM interface
```

**Applying this:**

| Capability         | Core or specific? | Reasoning                                        |
| ------------------ | ----------------- | ------------------------------------------------ |
| Memory             | **Core**          | Every complex agent needs to remember            |
| Document ingestion | **Core**          | Most agents need to read files                   |
| Code execution     | **Core**          | Huge unlock for any agent                        |
| Browser            | **Core**          | 80%+ of useful tasks involve web                 |
| Web extraction     | **Specific**      | Uses core (browser), but specific patterns/tools |
| Research synthesis | **Specific**      | Composition of core primitives + prompts         |

**So the core engine becomes:**

```
agnt core
├── LLM interface (model-agnostic)
├── Tool system
├── Subagent orchestration
├── Memory / state
├── Document ingestion
├── Code execution (sandboxed)
├── Browser (optional, but built-in)
└── Primitives that compose
```

Then web extraction is: browser + custom tools + specific prompts. Built WITH agnt, not part of it.

**This is more compelling because:**

- Every improvement to core raises all agents
- You're building infrastructure, not just one product
- Developers can build their own agents on a powerful foundation
- Your own agents (scraping, etc.) are just first examples

---

# Manus

**Manus core capabilities:**

Manus orchestrates a suite of specialized sub-agents (for planning, knowledge retrieval, code generation, etc.), which work together in parallel to handle complex workflows.

It can start with a single prompt and produce a dashboard without additional prompts. They run in a Linux sandbox where they can install software, run scripts, and execute shell commands.

**Their use cases:**

| Use case                                                                                                                 | What it requires                                 |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| Extracting key details from multiple resumes, comparing qualifications, providing ranked list, exporting to spreadsheets | Document ingestion + memory + synthesis + output |
| Filtering properties, writing Python to calculate affordability, compiling reports                                       | Browser + code execution + document generation   |
| Fetching stock data, performing correlation analysis, writing code for visualization                                     | Data extraction + code execution + synthesis     |
| Batch analyzing contracts, financial statements, user feedback to extract key information                                | Document ingestion + synthesis                   |
| Converting a research paper into a PPT                                                                                   | Document ingestion + document generation         |

**What this tells us about core engine:**

Their power comes from core primitives:

```
agnt core should have:
├── Browser (web navigation, interaction)         ✅ You have
├── Code execution (Python, shell)                ✅ You have
├── Document ingestion (PDFs, docs, spreadsheets) ❌ Need
├── Memory (persist across steps)                 ❌ Need
├── Document generation (reports, slides, CSV)    ❌ Need
├── Sub-agent orchestration                       ✅ You have
└── Async/background execution                    ~ Partial
```

**To match their surface area, add to core:**

```
Priority order for core engine:

1. Code execution (sandboxed)
   → Unlocks: analysis, visualization, computation

2. Document ingestion
   → Unlocks: research papers, PDFs, resume screening

3. Memory
   → Unlocks: multi-step reasoning, comparisons

4. Document generation
   → Unlocks: reports, slides, spreadsheets as output
```

**With these four additions + what you have:**

You can do everything Manus does, but open and self-hostable.

**Is "match Manus use cases" a good strategy?**

Yes, as a benchmark. Their use cases represent validated demand — people actually want these things done. But your advantage isn't copying them, it's:

- Open engine others can build on
- Reliable execution (your scraping background)
- Extensible architecture
- No waitlist, no trust issues

**The plan:**

```
agnt core (the engine):
├── Browser                    ✅ Have
├── Sub-agent orchestration    ✅ Have
├── Code execution             ← Add
├── Document ingestion         ← Add
├── Memory                     ← Add
├── Document generation        ← Add

With this core, you can build:
├── Any Manus use case
├── Plus things they can't do (your scraping depth)
└── And others can build their own agents
```

Does this answer both questions? Core engine focus + Manus as a capability benchmark?
