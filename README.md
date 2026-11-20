# Database Performance Diagnosis Assistant

A simulated, evidence-driven database troubleshooting assistant that compares five classical AI agents with one local Ollama LLM agent. All six agents analyze the same selected scenario and return a consistent diagnosis structure.

> **Safety and scope:** This is a simulation. The four diagnostic tools read an in-memory scenario dataset. The application does not connect to a production database, execute SQL, create/drop indexes, alter tables, or change database configuration.

## 1. Project objectives

- Implement five distinct classical intelligent-agent architectures:
  - Simple Reflex Agent
  - Model-Based Reflex Agent
  - Goal-Based Agent
  - Utility-Based Agent
  - Learning Agent
- Implement a local LLM agent using Ollama (Qwen3 by default) and LangChain tool calling.
- Give all six agents the same selected database scenario evidence.
- Demonstrate normal, critical, and ambiguous conditions.
- Display decisions, evidence, reasoning, recommendations and verification metrics in Streamlit.
- Persist human feedback so that the Learning Agent's future action ranking can change.

## 2. Architecture

```text
                   Selected scenario (one shared object)
                                  |
            +---------------------+---------------------+
            |                                           |
     Five classical agents                     Ollama LLM agent
            |                                           |
            |                                   LangChain tool calls
            |                                           |
            |                         +-----------------+------------------+
            |                         |                 |                  |
            |                    DB metrics        Query plan          DB logs
            |                         |                 |                  |
            |                         +------------ Index metadata --------+
            |                                           |
            +----------------------+--------------------+
                                   |
                         Standardized agent results
                                   |
                         Streamlit comparison UI
                                   |
                       Learning feedback → JSON store
```

### Agent decision mechanisms

| Agent | Decision mechanism | What makes it distinct |
|---|---|---|
| Simple Reflex | Current observation → condition/action rule | Stateless; does not use stored experience or an environment model |
| Model-Based Reflex | Observation → update internal model → state-based action | Keeps beliefs between runs with a persistence counter and a latency trend. A belief seen once is "tentative" (lower confidence); after 2 consecutive observations it is "confirmed" (higher confidence) |
| Goal-Based | Explicit goals → goal-relevant diagnostic plan | Selects actions to support diagnosis, responsiveness and safety goals |
| Utility-Based | Score possible actions → choose maximum utility | Weighs benefit, safety, feasibility and risk |
| Learning | Historical feedback → adjusted action ranking | Uses stored success/failure outcomes to influence future recommendations |
| Ollama LLM | Model → actual tool calls → evidence-grounded response | Uses a local language model and read-only LangChain tools |

### Shared agent result format

Each agent returns the same core fields: `symptom_summary`, `evidence`, `likely_bottleneck`, `recommendations`, `verification_metric`, `reasoning`, `confidence`, `selected_action_id`, and `status`. The LLM also returns its tool-call trace and tool outputs.

## 3. Simulated scenarios

| ID | Scenario | Primary evidence | Expected diagnosis direction |
|---|---|---|---|
| N | Normal performance | Low latency, normal CPU/pool usage, index seek | No immediate bottleneck; keep monitoring |
| A | Frequent slow query / full table scan | High latency, full table scan, no relevant index listed | Investigate query access path and index design |
| B | Connection-pool saturation | Pool at 100%, waiting requests, acquisition timeout logs | Investigate connection waits and connection lifecycle |
| C | Peak traffic / resource pressure | CPU 92%, pool 95%, request rate 3× baseline | Correlate peak workload, CPU, connections and expensive queries |
| D | Ambiguous/incomplete evidence | Elevated latency, unavailable query plan, incomplete logs/index metadata | Collect missing evidence; do not guess the root cause |

All values are synthetic demonstration data, not measurements from a real database.

## 4. Read-only diagnostic tools

The LLM can use these LangChain tools:

1. `get_database_metrics()` — query latency, CPU, request traffic, active connections and pool usage.
2. `inspect_query_plan()` — plan availability, operation, rows scanned and index usage.
3. `search_database_logs(keyword="")` — return all selected scenario log lines, or the lines that contain every word of the keyword in any order. If nothing matches, the result includes a hint to search again with an empty keyword.
4. `get_index_metadata()` — read the selected scenario's available index names and indexed columns.

**Safety guard.** The model is told to recommend only read-only diagnostics, but a local model does not always follow that. The code therefore checks every LLM recommendation. If one would change schema or configuration (for example "Increase the maximum number of connections in the pool"), it is relabelled "Proposal for DBA review (not executed): …", and the UI shows a notice. Nothing is ever executed.

At least two **distinct, relevant tools must successfully execute** before the LLM result is reported as successful. The application displays the actual tool-call trace and results. A model response that does not satisfy the minimum is reported as a tool-call failure rather than being presented as grounded analysis.

Tool availability by scenario:

| Scenario | Relevant tools expected |
|---|---|
| N | Metrics, query plan |
| A | Metrics, query plan, index metadata |
| B | Metrics, database logs |
| C | Metrics, database logs, query plan |
| D | Metrics, query plan, database logs |

## 5. Learning design

The Learning Agent ranks relevant candidate actions using:

```text
score = 0.70 × smoothed_success_rate
      + 0.20 × diagnostic_value
      + 0.10 × safety
```

The smoothed rate is `(successes + 1) / (successes + failures + 2)`. This avoids allowing one early outcome to dominate. The observed success rate is also displayed separately.

After a diagnostic action has actually been tried, the user can mark the Learning Agent's selected action as successful or unsuccessful. The counts are stored in `data/learning_history.json`. Running the agent again reloads the data and recalculates action scores. Only record feedback that reflects an observed outcome; do not mark an action successful merely because it was recommended.

For a clean demonstration, reset `data/learning_history.json` to:

```json
{
  "actions": {}
}
```

## 6. Requirements

- Python 3.11 or 3.12 recommended (3.10+ supported). The suite also passes on 3.14, but third-party `langsmith` then emits deprecation warnings.
- Ollama installed and running locally for the LLM feature
- A tool-capable Ollama model such as Qwen3 downloaded locally
- Python packages listed in `requirements.txt`

The five classical agents and most of the dashboard can be exercised without Ollama. The LLM panel reports a setup/runtime message if the Ollama service, model or LangChain dependency is unavailable.

## 7. Installation and run instructions

### Windows PowerShell

From the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use the following for the current terminal session, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Install and test the local Ollama model

Install Ollama using the official instructions for your operating system: <https://ollama.com/download>.

Then open a terminal and run:

```bash
ollama pull qwen3
ollama run qwen3
```

Exit the interactive model prompt after confirming the model responds. Leave the Ollama service running. The default endpoint used by the application is `http://localhost:11434`; change it in the Streamlit sidebar if your local setup uses a different endpoint.

### Start the application

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit in your browser. Select a scenario and click **Run all six agents**. The classical agents run first; the LLM agent then requests evidence using its tools.

### Run automated tests

From the project root, with the virtual environment activated:

```bash
pytest -v
```

The automated tests cover scenario completeness, defensive copying, read-only tools, standardized classical-agent results, Model-Based memory (belief persistence and latency trend), evidence-based classification (no scenario-ID shortcuts), utility rankings, learning feedback changing the selected action, the per-run comparison, and the LLM tool-calling loop. The LLM loop is tested with a fake chat model that issues real tool calls, so success with two distinct tools, failure with only one tool, and non-JSON answers are all checked without a live Ollama server. A live LLM demonstration is a separate integration check described below.

To print the classical-agent comparison table for all five scenarios (uses a temporary learning store):

```bash
python -m evaluation.generate_comparison
```

## 8. LLM integration check

To verify real local tool calling:

1. Confirm Ollama is running.
2. Confirm the model is present with `ollama list`.
3. Start the Streamlit application.
4. Select Scenario A, B or C and run all agents.
5. Expand **Ollama LLM Agent**.
6. Confirm at least two distinct relevant tools have `status: success` in the tool-call trace.
7. Expand **View tool return values** and compare the metrics/plan/log/index evidence with the selected scenario.
8. Confirm the LLM's displayed evidence comes from those returned tool results.

Passing the offline unit tests does not by itself prove that a live LLM run works, so the live tool-calling runs are recorded separately in `TEST_RESULTS.md`, section 5.

## 9. Test results

The offline validation record is in [`TEST_RESULTS.md`](TEST_RESULTS.md). The automated suite reports **49 passed** (see `screenshots/pytest_summary.png`). The live Ollama/Qwen3 tool-calling check was run for every scenario. Its results and screenshots are in `TEST_RESULTS.md`, sections 2 and 5.

## 10. Evaluation and screenshots

All screenshots are in `screenshots/` and embedded in `TEST_RESULTS.md`:

| What | Files |
|---|---|
| Each scenario: shared evidence, Goal/Utility panels, six-agent comparison, LLM diagnosis and tool trace | `scenario_<N/A/B/C/D>_1_overview_*.png`, `_2_agents_*.png`, `_3_comparison_*.png`, `_4_llm_*.png` |
| Model-Based memory (C run twice: belief confirmed, confidence 82% → 89%) | `model_based_memory_1.png`, `model_based_memory_2.png` |
| Learning before and after one Unsuccessful outcome | `learning_before.png`, `learning_after.png`, `learning_after_2.png` |
| Automated test run (49 passed) | `pytest_run_1.png`, `pytest_run_2.png`, `pytest_summary.png` |

### Comparison table (classical agents, empty learning history)

Output of `python -m evaluation.generate_comparison`. Format: bottleneck (selected action, confidence). The LLM column comes from the live run recorded in `TEST_RESULTS.md`.

| Scenario | Simple Reflex | Model-Based (1st run) | Goal-Based | Utility-Based | Learning |
|---|---|---|---|---|---|
| N: Normal | No immediate bottleneck (rule, 88%) | No immediate bottleneck (state reflex, 81%) | No immediate bottleneck (`goal_preserve_healthy_baseline`, 93%) | No immediate bottleneck (`verify_baseline_metrics`, 92%) | No immediate bottleneck (`verify_baseline_metrics`, 62%) |
| A: Full table scan | Full table scan (rule, 94%) | Full table scan (state reflex, 86%) | Full table scan (`goal_review_query_and_index_design`, 93%) | Full table scan (`inspect_query_plan`, 96%) | Full table scan (`inspect_query_plan`, 63%) |
| B: Pool saturation | Pool saturation (rule, 92%) | Pool saturation (state reflex, 85%) | Pool saturation (`goal_review_connection_lifecycle`, 93%) | Pool saturation (`inspect_pool_waits`, 96%) | Pool saturation (`inspect_pool_wait_time`, 63%) |
| C: Peak traffic | Peak-load contention (rule, 91%) | Peak-load contention (state reflex, 82%) | Peak-load contention (`goal_correlate_peak_load`, 93%) | Peak-load contention (`correlate_peak_metrics`, 96%) | Peak-load contention (`correlate_peak_load`, 63%) |
| D: Ambiguous | Insufficient evidence (rule, 55%) | Incomplete evidence (state reflex, 56%) | Incomplete evidence (`goal_collect_missing_evidence`, 93%) | Incomplete evidence (`collect_missing_evidence`, 96%) | Incomplete evidence (`collect_missing_evidence`, 63%) |

The agents agree on the bottleneck because the evidence in each scenario points one way. They differ in the action they choose, their confidence, and how they justify it:

- In scenario C, CPU (92%) and pool usage (95%) are both high. Simple Reflex checks the peak-load rule before the pool rule, so it does not misreport C as a pool problem.
- Model-Based confidence is lower on the first run, because its belief is "tentative". Running the same scenario again confirms the belief and raises confidence by about 7 points.
- Goal-Based rejects "Increase pool size immediately" in B and "Raise limits without workload analysis" in C, because those plans do not satisfy the safety and diagnosis goals.
- Utility-Based picks the narrowest, safest diagnostic step (for example `inspect_query_plan` at 0.964 against `review_index_design` at 0.892 in A).
- Learning has low confidence (about 62%) with no history, because every action starts at a 0.50 prior. After three failures are recorded for `inspect_query_plan` in A, it switches to `review_index_design`.
- In D, the agents that score candidates (Goal, Utility, Learning) report high confidence in their *action* (collect evidence). The reflex agents report low confidence in a *diagnosis*.

### Why decisions differ

- Simple Reflex applies the first matching direct rule.
- Model-Based Reflex updates and consults an internal representation of the selected environment, including how many consecutive observations support each belief and whether latency is rising or falling.
- Goal-Based selects a plan based on explicit objectives and safety constraints.
- Utility-Based computes action scores and picks the maximum-scoring candidate.
- Learning ranks candidates using previously recorded outcomes, so its preferred action may change after feedback.
- The LLM interprets evidence returned by its tools and generates a natural-language diagnosis; it can still make mistakes, so the tool trace and evidence must be reviewed.

## 11. Limitations and future improvements

- All measurements, logs, query plans and index metadata are simulated.
- The Learning Agent learns from user-reported feedback, not automatically verified database outcomes.
- Learning statistics are stored per action, not per scenario. `inspect_query_plan` is a candidate in both A and D, so feedback recorded in one scenario also affects the other.
- The Model-Based agent's memory lives in the Streamlit session and is lost when the browser session ends.
- The bottleneck categories and thresholds are shared across the classical agents, so they mostly agree on the bottleneck. Their differences show up in the selected action, confidence and justification.
- The LLM requires a compatible local Ollama model and may fail to call tools or produce valid JSON; those failures are shown rather than hidden.
- The utility weights and agent thresholds are transparent demonstration parameters, not universal database tuning rules.
- A production version would need authenticated telemetry ingestion, real query-plan sampling, access controls, audit logging, workload-specific thresholds and human approval for any proposed change.

## 12. Project layout

```text
Database-Performance-Diagnosis/
├── app.py
├── agents/
│   ├── __init__.py
│   ├── common.py
│   ├── simple_reflex.py
│   ├── model_based.py
│   ├── goal_based.py
│   ├── utility_based.py
│   ├── learning_agent.py
│   └── llm_agent.py
├── database/
│   ├── __init__.py
│   ├── scenarios.py
│   └── database_tools.py
├── learning/
│   ├── __init__.py
│   └── experience_store.py
├── evaluation/
│   ├── __init__.py
│   ├── comparison.py
│   └── generate_comparison.py
├── data/
│   └── learning_history.json
├── tests/
│   ├── test_agents.py
│   ├── test_scenarios.py
│   ├── test_learning.py
│   └── test_llm_agent.py
├── screenshots/
├── requirements.txt
├── README.md
└── TEST_RESULTS.md
```
