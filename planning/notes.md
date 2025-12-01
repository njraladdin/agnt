## The Anthropic Pattern for Long-Running Agents

https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
**The Core Mechanism:**
To make agents work over days/weeks, treat them like "Shift Workers" who arrive with zero memory and must rely on written documentation.

**1. The "Architect vs. Builder" Split**
Never start coding immediately.

- **Session 1 (Architect):** dedicated purely to setup. It creates the environment, initiates Git, and writes a detailed JSON roadmap.
- **Session 2+ (Builders):** dedicated to executing the roadmap one item at a time.

**2. "Hard State" over Context Window**
Since context resets, memory must be stored in files:

- **Roadmap (JSON):** A rigid checklist of features (Pending/Done).
- **Journal (TXT):** A human-readable handover note for the next agent.
- **Version Control (Git):** To allow the agent to revert its own mistakes.

**3. The Boot Protocol**
Every agent session must start with an orientation phase _before_ writing code:

1.  **Read:** Check the Journal and Git logs.
2.  **Verify:** Run the app to ensure the _previous_ agent didn't leave it broken.
3.  **Pick:** Select exactly **one** feature from the Roadmap.

**4. Visual Verification**
Agents often hallucinate that unit tests passed. Force the agent to use browser automation tools (like Puppeteer) to "see" that a feature works end-to-end before marking it complete.

## EVO-MEMORY: SELF-EVOLVING AGENT ARCHITECTURE (GOOGLE DEEPMIND)

https://arxiv.org/abs/2511.20857

1. THE CORE CONCEPT: TEST-TIME EVOLUTION (TTL)
   Standard agents use static memory (RAG) to recall facts ("What did user say?").
   Evo-Memory agents use dynamic memory to reuse experience ("How did I solve this last time?").

   - The Goal: Move from "Conversational Recall" (Facts) to "Experience Reuse" (Strategies).
   - The Method: The agent must actively curate its own memory database during deployment, without model training.

2. THE "ReMem" LOOP (Think - Act - Refine)
   Instead of the standard `Think -> Act` loop, introduce a third explicit step:

   A. Think: Decompose the task.
   B. Act: Execute tool use or code.
   C. REFINE (The "Evo" Step):
   After an action/task is complete, the agent performs meta-reasoning on its memory.
   It does not just log the result; it edits the database.

3. MEMORY OPERATIONS (HOW EVOLUTION HAPPENS)
   The agent is given specific tools to manage its "Wisdom Database":

   - Pruning (Forgetting):
     The agent identifies specific Memory IDs that were retrieved but unhelpful or distracting.
     It explicitly commands the system to delete them to reduce noise for future shifts.
   - Generalization (Abstracting):
     The agent takes a specific success (e.g., "I fixed the numpy import error by downgrading to v1.21") and rewrites it as a general rule ("When using library X, pin version to Y").
   - Synthesis (Merging):
     Combining multiple fragmented experiences into a single, high-quality strategy.

4. THE "COLD START" RETRIEVAL STRATEGY
   When starting a new task, the agent retrieves experiences based on _Task Similarity_, not just keyword matching.

   - Input: Current Task Goal.
   - Retrieval: Finds the "Top-K" past strategies.
   - Context Construction: The prompt includes "Relevant Experience from Similar Tasks."
   - Result: The agent sees the _failure modes_ of previous sessions before it generates its first line of code.

5. PROMPTING MECHANIC (FROM IMPLEMENTATION)
   The agent's output space is expanded. It doesn't just output text/code. It outputs standardized memory commands:
   - Format 1 (Prune): `Think-Prune: <IDs>` -> Remove bad context.
   - Format 2 (Reason): `Think: <Reasoning>` -> Standard CoT.
   - Format 3 (Execute): `Action: <Command>` -> Standard Tool use.
