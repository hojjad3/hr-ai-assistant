# hr-ai-assistant
HR AI assistant backend with LangGraph

## Setup
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt` (or run `uv sync` if you prefer uv)
3. Add your free GROQ_API_KEY in a `.env` file at the project root.
4. Run `python main.py` or `uv run main.py`

## Design Decisions

### LLM Choice
We are using `openai/gpt-oss-20b` via Groq. It serves as an effective, efficient open-source equivalent for general QA, routing, and tool calling at lower latency and zero cost, satisfying the assignment's free tier requirement. (If you prefer running fully local without an API key, you can swap `ChatGroq` for `ChatOllama` in `app/agent.py` and run Ollama locally).

### Chunking Approach
The PDFs are split using a `RecursiveCharacterTextSplitter` with a 1000-character chunk size and 250-character overlap. This size strikes a balance: it is large enough to preserve policy context (full sections usually stay together), but small enough to ensure dense vectors for accurate retrieval via `all-MiniLM-L6-v2`. The overlap prevents critical sentences from being split across boundaries.

### Routing Logic
The system uses tool calling to route questions. The system prompt directs the LLM to use:
- `query_employee_data_tool` for personal data, aggregations, and cross-employee queries (leave balance, budget, team lists, counts).
- `policy_search_tool` for general processes and policy questions.
- Both tools simultaneously for hybrid questions (e.g., "Can I take Friday off?" requires checking both leave balance and policy rules).

If the LLM doesn't call a tool, or if the retrieved tools do not ground an answer, the agent falls back to stating "I don't know". Furthermore, the `policy_search` tool enforces an L2 distance relevance threshold, ensuring the model genuinely sees "no relevant policy content found" instead of hallucinating based on irrelevant text.

### Limitations & Edge Cases
1. **Source Tie-Break Rule**: If a single query results in both `query_employee_data_tool` and `policy_search_tool` tools being executed by the LLM, the `source` field assigned in the API response will be based on the tool that was consulted *last*. The schema natively only supports "rag", "structured_data", or "unknown", so this tie-break rule correctly forces conformity.
2. **Auth Model**: The `POST /ask` endpoint strictly accepts `{"employee_id": str, "question": str}` payloads with no complex token headers, cleanly adhering to the assessment specs. However, the *Frontend* (NiceGUI) implements a dedicated `/login` page with mock password verification, maintaining state securely in browser storage before constructing the raw payload to the backend.
3. **Conversational Memory (Bonus)**: We implemented full, persistent conversational memory using LangGraph's `SqliteSaver`. The API strictly adheres to the stateless `{"employee_id": str, "question": str}` schema by generating a new thread ID per request (preventing test hallucination). However, the frontend passes an optional `session_id`, allowing real users to experience a complete, persistent chat history that survives server restarts! All chat data is securely stored in `data/chat_history.sqlite`.

### Data Security & Privacy (Code Review Note)
Because this application processes mock PII (such as performance ratings and leave balances), the current implementation uses the Groq API for rapid prototyping. However, for a production environment—especially in regions with strict data privacy laws (like the KSA PDPL)—sending employee PII to a third-party cloud provider without enterprise agreements may pose a compliance risk. For a fully private, production-ready deployment, the `ChatGroq` model in `app/agent.py` can be seamlessly swapped for a local `ChatOllama` model (as permitted by the assignment stack), ensuring no employee data ever leaves your internal infrastructure. Additionally, a true enterprise Identity Provider (IdP) via SSO would replace the current mock login implementation.

## Example Questions & Responses

These questions have been tested (via `tests/test_questions.py`) using `EMP001` (who has 18 leave days and $1200 training budget).

**Q1:** "How many annual leave days do I have left?"
- **Answer:** "You have 18 annual leave days remaining."
- **Source:** `structured_data` (routed to `employee_lookup_tool`)

**Q2:** "How much training budget do I have remaining this year?"
- **Answer:** "Your remaining training budget for this year is $1,200."
- **Source:** `structured_data` (routed to `employee_lookup_tool`)

**Q3:** "What's the process for requesting to work remotely?"
- **Answer:** "To request to work remotely, you must submit a formal request via the HR portal at least two weeks in advance. The request requires approval from your direct manager."
- **Source:** `rag` (routed to `policy_search_tool` using `policy_02_remote_work.pdf`)

**Q4:** "Can my training budget be used for a professional conference?"
- **Answer:** "Yes, the training budget can be applied toward courses, certifications, workshops, and professional conferences directly related to your role."
- **Source:** `rag` (routed to `policy_search_tool` using `policy_05_training_development.pdf`)

**Q5:** "What's the office WiFi password?"
- **Answer:** "I don't know the answer to that. I only have access to HR policies and employee data."
- **Source:** `unknown` (The LLM correctly identifies that it cannot answer and refuses to hallucinate)
