"""Streamlit dashboard for the Database Performance Diagnosis Assistant."""
from __future__ import annotations

import streamlit as st

from agents.goal_based import GoalBasedAgent
from agents.learning_agent import LearningAgent
from agents.llm_agent import LLMDiagnosisAgent
from agents.model_based import ModelBasedReflexAgent
from agents.simple_reflex import SimpleReflexAgent
from agents.utility_based import UtilityBasedAgent
from database.scenarios import get_scenario, list_scenarios
from evaluation.comparison import (
    build_comparison_rows,
    consensus_category,
    explain_agent_differences,
    explain_run_differences,
)
from learning.experience_store import ExperienceStore


st.set_page_config(
    page_title="Database Performance Diagnosis Assistant",
    page_icon="🛠️",
    layout="wide",
)

st.title("Database Performance Diagnosis Assistant")
st.caption("Six intelligent agents · shared simulated evidence · safe, evidence-based recommendations")
st.info(
    "This project uses simulated database telemetry. Its diagnostic tools are read-only and do not connect to or modify a production database.",
    icon="ℹ️",
)

# Keep the model-based agent's internal model in this browser session.
if "model_based_agent" not in st.session_state:
    st.session_state.model_based_agent = ModelBasedReflexAgent()
if "agent_results" not in st.session_state:
    st.session_state.agent_results = None
if "previous_scenario_id" not in st.session_state:
    st.session_state.previous_scenario_id = None

with st.sidebar:
    st.header("Diagnosis settings")
    scenario_options = list_scenarios()
    scenario_ids = [item["scenario_id"] for item in scenario_options]
    selected_id = st.selectbox(
        "Select database scenario",
        options=scenario_ids,
        format_func=lambda key: f"{key} — {next(x['scenario_name'] for x in scenario_options if x['scenario_id'] == key)}",
    )
    st.divider()
    st.subheader("Local LLM configuration")
    ollama_model = st.text_input("Ollama model", value="qwen3", help="Must already be downloaded with `ollama pull`." )
    ollama_url = st.text_input("Ollama base URL", value="http://localhost:11434")
    ollama_reasoning = st.checkbox(
        "Enable model thinking (slower)",
        value=False,
        help="Qwen3 'thinking' mode reasons before each answer. It is usually 2-5x slower and is not required for tool calling.",
    )
    st.caption("The five classical agents can run without Ollama. The LLM panel reports a clear setup error if the local model is unavailable.")

if st.session_state.previous_scenario_id != selected_id:
    st.session_state.agent_results = None
    st.session_state.previous_scenario_id = selected_id

scenario = get_scenario(selected_id)
metrics = scenario["database_metrics"]

st.subheader(f"Scenario {selected_id}: {scenario['scenario_name']}")
st.write(scenario["description"])

metric_columns = st.columns(5)
metric_values = [
    ("Average latency", f"{metrics['avg_query_latency_ms']:,} ms"),
    ("P95 latency", f"{metrics['p95_query_latency_ms']:,} ms"),
    ("Database CPU", f"{metrics['cpu_percent']}%"),
    ("Pool utilization", f"{metrics['pool_usage_percent']}%"),
    ("Active connections", f"{metrics['active_connections']}/{metrics['max_connections']}"),
]
for column, (label, value) in zip(metric_columns, metric_values):
    column.metric(label, value)

with st.expander("Inspect the shared scenario evidence", expanded=False):
    left, right = st.columns(2)
    with left:
        st.markdown("**Database metrics**")
        st.json(scenario["database_metrics"])
        st.markdown("**Query plan**")
        st.json(scenario["query_plan"])
    with right:
        st.markdown("**Index metadata**")
        st.json(scenario["index_metadata"])
        st.markdown("**Database logs**")
        st.write(scenario["logs"])
        st.caption(f"Log sample complete: {scenario['logs_complete']}")

st.divider()
st.subheader("Run the six agents")
st.write("All agents receive the same selected scenario object. The Learning Agent additionally consults its persistent experience history; the LLM retrieves evidence through read-only tools.")

if st.button("Run all six agents", type="primary", use_container_width=True):
    experience_store = ExperienceStore()
    agents = [
        SimpleReflexAgent(),
        st.session_state.model_based_agent,
        GoalBasedAgent(),
        UtilityBasedAgent(),
        LearningAgent(experience_store),
    ]
    current_results: dict[str, dict] = {}
    progress = st.progress(0, text="Running classical agents...")
    for index, agent in enumerate(agents, start=1):
        try:
            current_results[agent.name] = agent.run(scenario)
        except Exception as exc:  # One agent failure should not hide the other results.
            current_results[agent.name] = {
                "agent_name": agent.name,
                "status": "error",
                "symptom_summary": "This agent could not complete its analysis.",
                "evidence": [],
                "likely_bottleneck": "Not determined",
                "recommendations": [],
                "verification_metric": "Resolve the implementation error and rerun.",
                "reasoning": str(exc),
                "confidence": 0.0,
                "selected_action_id": "",
                "error": str(exc),
            }
        # Five classical agents fill the first 5/6 of the bar; the LLM fills the rest.
        progress.progress(index / 6, text=f"Completed {agent.name}...")

    progress.progress(5 / 6, text="Calling the local Ollama LLM...")
    with st.spinner(f"Waiting for {ollama_model} to investigate with tools..."):
        llm_agent = LLMDiagnosisAgent(model=ollama_model, base_url=ollama_url, reasoning=ollama_reasoning)
        current_results[llm_agent.name] = llm_agent.run(scenario)
    progress.progress(1.0, text="Analysis complete.")
    st.session_state.agent_results = current_results

results = st.session_state.agent_results
if results:
    st.divider()
    st.subheader("Agent decisions and reasoning")
    for agent_name, result in results.items():
        is_success = result.get("status") == "success"
        title = f"{agent_name} — {result.get('likely_bottleneck', 'No result')}"
        with st.expander(title, expanded=(agent_name == "Learning Agent")):
            if not is_success:
                st.warning(result.get("error", "Agent did not complete successfully."))
                if result.get("raw_response"):
                    st.code(result["raw_response"], language="text")
            st.markdown(f"**Status:** `{result.get('status', 'unknown')}`")
            st.markdown(f"**Symptom summary:** {result.get('symptom_summary', '—')}")
            st.markdown(f"**Likely bottleneck:** {result.get('likely_bottleneck', '—')}")
            st.markdown("**Evidence**")
            for item in result.get("evidence", []):
                st.write(f"• {item}")
            st.markdown("**Recommendations**")
            for item in result.get("recommendations", []):
                st.write(f"• {item}")
            st.markdown(f"**Verification metric:** {result.get('verification_metric', '—')}")
            st.markdown(f"**Reasoning:** {result.get('reasoning', '—')}")
            if is_success:
                st.progress(float(result.get("confidence", 0.0)), text=f"Confidence: {float(result.get('confidence', 0.0)):.0%}")
            if result.get("candidate_scores"):
                st.markdown("**Candidate action scores**")
                st.dataframe(result["candidate_scores"], hide_index=True, use_container_width=True)
            if result.get("plan_evaluation"):
                st.markdown(f"**Goal evaluation** — required goals: {', '.join(result.get('required_goals', []))}")
                st.dataframe(
                    [
                        {
                            "Plan": item["label"],
                            "Goals achieved": ", ".join(item["achieved_goals"]) or "none",
                            "All required goals satisfied": "Yes (selected)" if item["action_id"] == result.get("selected_action_id") else ("Yes" if item["all_goals_satisfied"] else "No (rejected)"),
                        }
                        for item in result["plan_evaluation"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            if result.get("internal_state"):
                st.markdown("**Model-based internal state**")
                st.json(result["internal_state"])
            if result.get("safety_flags"):
                st.info(
                    f"Safety guard: {len(result['safety_flags'])} LLM recommendation(s) proposed a schema or "
                    "configuration change. They were relabelled as proposals for DBA review; nothing is executed.",
                    icon="🛡️",
                )
            if result.get("tool_calls") is not None:
                st.markdown("**Actual LLM tool-call trace**")
                if result["tool_calls"]:
                    st.dataframe(result["tool_calls"], hide_index=True, use_container_width=True)
                else:
                    st.caption("No tool calls were completed in this run.")
                if result.get("tool_results"):
                    st.markdown("**Returned tool evidence**")
                    st.json(result["tool_results"])

    st.divider()
    st.subheader("Six-agent comparison")
    rows = build_comparison_rows(results)
    st.dataframe(rows, hide_index=True, use_container_width=True)
    consensus = consensus_category(results)
    agreeing = sum(1 for row in rows if row["Agrees with consensus"] == "Yes")
    completed = sum(1 for row in rows if row["Status"] == "success")
    if consensus:
        st.markdown(f"**Consensus:** {agreeing}/{completed} completed agents point to **{consensus}**.")
    st.markdown("**Why the decisions differ in this run**")
    st.dataframe(explain_run_differences(results), hide_index=True, use_container_width=True)
    with st.expander("Decision mechanism of each agent (general)"):
        st.dataframe(explain_agent_differences(), hide_index=True, use_container_width=True)

    learning_result = results.get("Learning Agent", {})
    if learning_result.get("status") == "success" and learning_result.get("selected_action_id"):
        st.divider()
        st.subheader("Learning Agent feedback")
        action_id = learning_result["selected_action_id"]
        action_label = LearningAgent.ACTIONS[action_id]["label"]
        st.write(f"Selected action: **{action_label}** (`{action_id}`)")
        st.caption("Record the observed outcome after the diagnostic action has actually been tried. This updates persistent experience data and can change future rankings.")
        with st.form("learning_feedback_form"):
            feedback = st.radio("Was this action successful?", ["Successful", "Unsuccessful"], horizontal=True)
            submitted = st.form_submit_button("Save learning feedback")
        if submitted:
            saved_stats = ExperienceStore().record_outcome(action_id, success=(feedback == "Successful"))
            st.success(
                f"Feedback saved. {saved_stats['successes']} successes, {saved_stats['failures']} failures; "
                f"observed success rate: {saved_stats['success_rate']:.0%}. "
                "Run the agents again to see the updated ranking."
            )

    with st.expander("Persistent learning history"):
        all_stats = ExperienceStore().get_all_stats()
        if all_stats:
            st.dataframe(
                [
                    {"Action ID": key, "Successes": value["successes"], "Failures": value["failures"], "Success rate": f"{value['success_rate']:.0%}"}
                    for key, value in all_stats.items()
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("No feedback has been recorded yet. Submit an outcome above to begin building experience.")
else:
    st.info("Select a scenario and click **Run all six agents** to view the diagnosis and comparison.")

st.divider()
st.caption("Safety boundary: the application is a simulator. It only reads scenario data and makes recommendations; it does not execute SQL or apply schema/configuration changes.")
