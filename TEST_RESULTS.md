# Test Results

**Test date:** 16 November 2026  
**Environment:** Windows (win32), Python 3.14.5, pytest 9.2.0, pluggy 1.7.0, PowerShell with a project virtual environment (`.venv`)

## 1. Automated test run

Command (run from the project root with the virtual environment activated):

```powershell
python -m pytest -v
```

Result:

```text
collected 49 items
...
49 passed, 13 warnings in 1.07s
```

All 49 tests passed. The 13 warnings are a `DeprecationWarning` raised inside the third-party `langsmith` package (`asyncio.iscoroutinefunction` is deprecated and slated for removal in Python 3.16). They come from a library, not from this project's code, and do not affect the results.

### Screenshots of the test run (49 passed)

Start of the run (platform, collected items, first tests):

![pytest run, part 1](screenshots/pytest_run_1.png)

Middle and end of the test list (100%):

![pytest run, part 2](screenshots/pytest_run_2.png)

Final summary line (`49 passed, 13 warnings`):

![pytest summary](screenshots/pytest_summary.png)

### What the 49 tests cover

| Test file | Tests | What is verified |
|---|---|---|
| `tests/test_scenarios.py` | 11 | All five scenarios (N, A, B, C, D) are present and share the same evidence schema. `get_scenario` returns an isolated copy. An unknown scenario gives a helpful error. The read-only tools return the expected evidence without changing scenario data. Log search matches all keyword words in any order (the live query "connection pool" now finds the timeout line), and gives a hint when nothing matches. |
| `tests/test_agents.py` | 26 | The five classical agents return a standardized result for all five scenarios. Simple Reflex applies the expected rule per scenario. Model-Based Reflex maintains internal state, uses it in the decision (tentative belief on run 1, confirmed and higher confidence on run 2), and tracks a rising latency trend. Utility and Learning agents diagnose from evidence even when the scenario ID is unknown. Peak traffic is not misclassified as pool-only pressure. Utility agent exposes ranked scores, and its "alternative considered" is never the selected action, even when scores tie. Goal-Based agent selects a plan that satisfies all required goals. Agents do not mutate the shared scenario. Learning experience changes the action ranking. One recorded failure for `inspect_query_plan` in A reproduces the documented demo exactly (0.626 → 0.509; `review_index_design` takes first place at 0.620), and the reasoning names the failed action. The comparison reports consensus, top recommendations and per-run reasons, and recognises varied LLM wording for a healthy result. |
| `tests/test_learning.py` | 4 | Feedback counts and rates persist. Invalid feedback is rejected. A corrupt history file is not silently overwritten. Reset clears experience. |
| `tests/test_llm_agent.py` | 8 | The LLM JSON parser accepts plain and fenced JSON and rejects invalid output. Displayed LLM evidence is built from tool results. With a fake tool-calling chat model: two distinct relevant tool calls give `success`, with evidence taken from real tool returns; a single tool call gives `tool_call_failed` after the agent re-prompts; a non-JSON answer gives `format_error`. The safety guard relabels schema/configuration-change recommendations from real qwen3 runs ("Increase the maximum number of connections…", "Consider creating a composite index…") as proposals for DBA review, and leaves read-only diagnostics unchanged. |

## 2. Scenario results (live application)

Model: `qwen3` through Ollama at `http://localhost:11434`, with thinking mode off. Learning history was empty and each scenario was run once with **Run all six agents**. The classical-agent cells match `python -m evaluation.generate_comparison`.

| Scenario | Simple Reflex | Model-Based | Goal-Based | Utility-Based | Learning | LLM (tools called) |
|---|---|---|---|---|---|---|
| N: Normal | No immediate bottleneck (88%) | No immediate bottleneck (81%) | `goal_preserve_healthy_baseline` (93%) | `verify_baseline_metrics` (92%) | `verify_baseline_metrics` (62%) | No significant bottleneck (95%); tools: `get_database_metrics`, `inspect_query_plan` |
| A: Full table scan | Full table scan (94%) | Full table scan (86%) | `goal_review_query_and_index_design` (93%) | `inspect_query_plan` (96%) | `inspect_query_plan` (63%) | Full table scan, 500,000 rows against 120 estimated (90%); tools: `inspect_query_plan`, `get_database_metrics` |
| B: Pool saturation | Pool saturation (92%) | Pool saturation (85%) | `goal_review_connection_lifecycle` (93%) | `inspect_pool_waits` (96%) | `inspect_pool_wait_time` (63%) | Pool saturation, timeouts confirmed by the log (95%); tools: `get_database_metrics`, `search_database_logs` |
| C: Peak traffic | Peak-load contention (91%) | Peak-load contention (82%)\* | `goal_correlate_peak_load` (93%) | `correlate_peak_metrics` (96%) | `correlate_peak_load` (63%) | High rows scanned under peak load with high CPU and connections (85%); tools: `get_database_metrics`, `inspect_query_plan` |
| D: Ambiguous | Insufficient evidence (55%) | Incomplete evidence (56%) | `goal_collect_missing_evidence` (93%) | `collect_missing_evidence` (96%) | `collect_missing_evidence` (63%) | "Unclear", no root cause assigned (60%); tools: `get_database_metrics`, `search_database_logs` |

\* 82% is the first run of C. The C comparison screenshot shows 92% because C had already been run twice in that browser session (observation #3, belief persistence 3). See section 3a.

Consensus on the bottleneck category was 6/6 in every scenario.

### Application screenshots

For each scenario: `1_overview` = selected scenario and shared evidence, `2_agents` = Goal-Based and Utility-Based panels, `3_comparison` = six-agent comparison and per-run reasons, `4_llm` = LLM diagnosis and tool-call trace.

#### Scenario N: Normal
![N overview](screenshots/scenario_N_1_overview_1.png)
![N evidence](screenshots/scenario_N_1_overview_2.png)
![N utility agent](screenshots/scenario_N_2_agents_1.png)
![N goal agent](screenshots/scenario_N_2_agents_2.png)
![N comparison](screenshots/scenario_N_3_comparison_1.png)
![N why decisions differ](screenshots/scenario_N_3_comparison_2.png)
![N LLM diagnosis](screenshots/scenario_N_4_llm_1.png)
![N LLM tool trace](screenshots/scenario_N_4_llm_2.png)

#### Scenario A: Full table scan
![A overview](screenshots/scenario_A_1_overview_1.png)
![A evidence](screenshots/scenario_A_1_overview_2.png)
![A goal agent](screenshots/scenario_A_2_agents_1.png)
![A utility agent](screenshots/scenario_A_2_agents_2.png)
![A comparison](screenshots/scenario_A_3_comparison_1.png)
![A why decisions differ](screenshots/scenario_A_3_comparison_2.png)
![A LLM diagnosis](screenshots/scenario_A_4_llm_1.png)
![A LLM tool trace](screenshots/scenario_A_4_llm_2.png)
![A LLM returned evidence](screenshots/scenario_A_4_llm_3.png)

#### Scenario B: Connection-pool saturation
![B overview](screenshots/scenario_B_1_overview_1.png)
![B evidence](screenshots/scenario_B_1_overview_2.png)
![B agents 1](screenshots/scenario_B_2_agents_1.png)
![B agents 2](screenshots/scenario_B_2_agents_2.png)
![B comparison](screenshots/scenario_B_3_comparison_1.png)
![B why decisions differ](screenshots/scenario_B_3_comparison_2.png)
![B LLM diagnosis](screenshots/scenario_B_4_llm_1.png)
![B LLM tool trace](screenshots/scenario_B_4_llm_2.png)

#### Scenario C: Peak traffic
![C overview](screenshots/scenario_C_1_overview_1.png)
![C evidence](screenshots/scenario_C_1_overview_2.png)
![C agents 1](screenshots/scenario_C_2_agents_1.png)
![C agents 2](screenshots/scenario_C_2_agents_2.png)
![C comparison](screenshots/scenario_C_3_comparison_1.png)
![C why decisions differ](screenshots/scenario_C_3_comparison_2.png)
![C LLM diagnosis](screenshots/scenario_C_4_llm_1.png)
![C LLM tool trace](screenshots/scenario_C_4_llm_2.png)

#### Scenario D: Ambiguous / incomplete evidence (edge case)
![D overview](screenshots/scenario_D_1_overview_1.png)
![D evidence](screenshots/scenario_D_1_overview_2.png)
![D agents 1](screenshots/scenario_D_2_agents_1.png)
![D agents 2](screenshots/scenario_D_2_agents_2.png)
![D comparison](screenshots/scenario_D_3_comparison_1.png)
![D why decisions differ](screenshots/scenario_D_3_comparison_2.png)
![D LLM diagnosis](screenshots/scenario_D_4_llm_1.png)
![D LLM tool trace](screenshots/scenario_D_4_llm_2.png)

## 3. Why the decisions differ

All six agents received the same scenario object. In N and A they agreed on the bottleneck (consensus 6/6), but they reached it in different ways and chose different actions:

- **Simple Reflex** fires the first matching rule on the current observation ("Inefficient query execution (full table scan)" in A). It uses no memory or scoring, and its confidence is fixed per rule.
- **Model-Based Reflex** first updates its internal state. On a first run, the belief is "tentative" (persistence = 1), so its confidence is lower than Simple Reflex (86% against 94% in A). Running the same scenario again confirms the belief and raises confidence.
- **Goal-Based** evaluates whole plans against explicit goals. In A it rejected "Inspect query plan only" because that plan does not meet `reduce_query_work`. In N it rejected "Make a proactive schema change" because it meets none of the goals.
- **Utility-Based** scores actions with 0.45×benefit + 0.35×safety + 0.20×feasibility − 0.20×risk. In A it chose `inspect_query_plan` (0.964) over `review_index_design` (0.891), because index review carries more risk and less feasibility.
- **Learning** has no history yet, so every action starts from a 0.50 prior. That makes its confidence the lowest (62–63%), and its ranking is decided by diagnostic value and safety only. Section 4 shows a recorded failure changing its choice.
- **LLM** chose which tools to call and wrote its own diagnosis. In A it called `inspect_query_plan` and `get_database_metrics`. It was the only agent to name the filter columns (`status`, `created_at`), which it read from the plan note. Its index idea was phrased as "Propose adding an index … for DBA review after validating with EXPLAIN on a test copy", so nothing is executed. Its wording changes when the prompt changes, so the comparison maps its answer to a category before checking agreement.
- **Edge case (D):** with the plan unavailable and logs incomplete, no classical agent assigned a root cause. The reflex agents report low confidence in a diagnosis (55–56%). Goal, Utility and Learning report high confidence in the *action* "collect missing evidence".

## 3a. Model-Based Reflex memory (scenario C, run twice)

Scenario C was run twice in the same browser session. On the second run, the agent used its stored internal state in the decision:

| Item | First run | Second run |
|---|---|---|
| `observation_count` | 1 | 2 |
| `belief_persistence.resource_pressure` | 1 | 2 |
| Evidence line | belief "tentative (first observation, not yet confirmed)" | belief "confirmed by 2 consecutive observations" |
| Latency trend | no previous observation | stable (900 ms) |
| Confidence | 82% | 89% |

The internal state also stores `previous_observation` (latency 900 ms, pool 95%, CPU 92%, `INDEX_SCAN`). The reasoning explains how memory was used: "belief 'resource_pressure' is confirmed by 2 consecutive observations, so the agent treats it as established". The Simple Reflex agent gives the same output on every run, so this is the behaviour that separates the two reflex agents.

![Model-Based memory, second run](screenshots/model_based_memory_1.png)
![Model-Based internal state](screenshots/model_based_memory_2.png)

## 4. Learning Agent before and after feedback

Scenario A was run with an empty history. The selected action (`inspect_query_plan`) was marked **Unsuccessful** in the UI, which wrote the outcome to `data/learning_history.json`, and A was run again.

Score = 0.70 × smoothed success rate + 0.20 × diagnostic value + 0.10 × safety, where smoothed rate = (successes + 1) / (successes + failures + 2).

| Candidate | Before: successes / failures | Before: score | After: successes / failures | After: score |
|---|---|---|---|---|
| `inspect_query_plan` | 0 / 0 | **0.626 (1st)** | 0 / 1 | 0.509 (3rd) |
| `review_index_design` | 0 / 0 | 0.620 (2nd) | 0 / 0 | **0.620 (1st)** |
| `inspect_slow_query_logs` | 0 / 0 | 0.618 (3rd) | 0 / 0 | 0.618 (2nd) |

One failure lowered the smoothed success rate of `inspect_query_plan` from 0.50 to 0.33, so its score fell by 0.117 and the agent switched its recommendation to `review_index_design`. The agent's reasoning states this directly: "Stored experience changed the ranking: 'Inspect query plan' has 0 success(es) and 1 failure(s) (smoothed success rate 0.33), so its score is 0.509. 'Review index design' now ranks first with 0.620." The **Persistent learning history** panel shows the stored record (`inspect_query_plan`: 0 successes, 1 failure, 0%).

Smoothing is deliberate. A single failure moves the action down, but does not rule it out, and it can recover after later successes.

![Learning Agent before feedback](screenshots/learning_before.png)
![Learning Agent after one Unsuccessful outcome](screenshots/learning_after.png)
![Persistent learning history after feedback](screenshots/learning_after_2.png)

`data/learning_history.json` was reset to `{"actions": {}}` after the demonstration, so the submitted project starts with no history.

## 5. Live LLM tool-calling check (Ollama)

Model: `qwen3` (local Ollama, thinking off), through `langchain_ollama.ChatOllama` with `bind_tools`.

| Scenario | Tools executed (all `success`) | Distinct tools | Result |
|---|---|---|---|
| N | `get_database_metrics`, `inspect_query_plan` | 2 | `success`, healthy |
| A | `inspect_query_plan`, `get_database_metrics` | 2 | `success`, full table scan; index idea phrased as a proposal for DBA review |
| B | `get_database_metrics`, `search_database_logs` (keyword "connection pool") | 2 | `success`, pool saturation; log search matched "ERROR: Timeout while acquiring a database connection from the pool." |
| C | `get_database_metrics`, `inspect_query_plan` | 2 | `success`, peak load; `INDEX_SCAN` of 45,000 rows under 3× traffic |
| D | `get_database_metrics`, `search_database_logs` (keyword "slow query") | 2 | `success`, cause reported as unclear; the keyword matched nothing, so the tool returned the full log sample, and the WARN line appears in the evidence |

Safety: in every run, recommendations that involve a schema or configuration change were phrased as proposals for DBA review. Examples are "Propose increasing the maximum number of connections in the pool for DBA review after validating…" (B) and "Propose adding an index on 'status' and 'created_at' … for DBA review" (A). No recommendation instructs an automatic change.

Evidence check: every LLM Evidence line is built by the application from the returned tool values, not from the model's text. In A, "query plan: FULL_TABLE_SCAN; rows scanned=500000; index used=False" and "average query latency: 2400 ms" match the `inspect_query_plan` and `get_database_metrics` returns in `scenario_A_4_llm_2.png` and `scenario_A_4_llm_3.png`.

## 6. Limitations

- The automated tests do not call a live Ollama model. They validate JSON parsing and evidence construction. Live tool calling is shown only by the section 5 check above.
- All measurements, logs, query plans and index metadata are simulated.
- The Learning Agent learns from user-reported feedback, not from automatically verified database outcomes.
