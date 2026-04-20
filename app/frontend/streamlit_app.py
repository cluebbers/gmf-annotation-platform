import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = 30


def call_api(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict | list:
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=API_TIMEOUT_SECONDS,
            json=body,
            params=params,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach backend at {API_BASE_URL}.") from exc

    if response.headers.get("content-type", "").startswith("application/json"):
        payload = response.json()
    else:
        payload = {"detail": response.text}

    if response.ok:
        return payload

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if not detail:
        detail = f"Request failed with status {response.status_code}."
    raise RuntimeError(str(detail))


def label_chips(labels: list[str]) -> str:
    if not labels:
        return "_None_"
    return "  ".join(f"`{label}`" for label in labels)


def format_incident_prompt(incident: dict) -> str:
    return (
        f"Incident data:\n"
        f"Title: {incident['title'] or 'N/A'}\n"
        f"Report Text:\n"
        f"{incident['report_text']}"
    )


def prediction_to_text(prediction: dict) -> str:
    known = ", ".join(prediction["known_ai_technical_failure"]) or "None"
    potential = ", ".join(prediction["potential_ai_technical_failure"]) or "None"
    return f"Known AI Technical Failure: {known}\nPotential AI Technical Failure: {potential}"


def build_chat_history(messages: list[dict]) -> list[dict[str, str]]:
    history = []
    for msg in messages:
        if msg["kind"] == "prediction_user":
            continue
        elif msg["kind"] == "prediction_assistant":
            history.append({
                "role": "assistant",
                "content": prediction_to_text(msg["result"]["prediction"]),
            })
        else:
            history.append({"role": msg["role"], "content": msg["content"]})
    return history


st.set_page_config(page_title="GMF Annotation Platform", layout="wide")

# ── Sidebar: incident selection ───────────────────────────────────────────────
with st.sidebar:
    st.title("GMF Annotation")
    st.caption(f"Backend: `{API_BASE_URL}`")

    try:
        incidents = call_api("GET", "/incidents")
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    search_query = st.text_input("Search", placeholder="ID, title, or report text…")
    query = search_query.strip().lower()
    filtered = [
        i for i in incidents
        if not query
        or query in str(i["id"])
        or query in (i["title"] or "").lower()
        or query in i["report_text"].lower()
    ]

    if not filtered:
        st.info("No incidents match.")
        st.stop()

    incident_labels = {
        i["id"]: f'#{i["id"]}{"  [gold]" if i["is_gold_set"] else ""}  {(i["title"] or "Untitled")[:55]}'
        for i in filtered
    }
    selected_id = st.selectbox(
        "Select incident",
        [i["id"] for i in filtered],
        format_func=lambda x: incident_labels[x],
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_annotate, tab_compare = st.tabs(["Annotate", "Compare"])

# ══════════════════════════════════════════════════════════════════════════════
# ANNOTATE TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_annotate:
    try:
        incident = call_api("GET", f"/incidents/{selected_id}")
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    if "conversations" not in st.session_state:
        st.session_state["conversations"] = {}
    if st.session_state.get("active_incident") != selected_id:
        st.session_state["active_incident"] = selected_id

    conversation: list[dict] = st.session_state["conversations"].get(selected_id, [])

    left_col, right_col = st.columns([2, 3], gap="large")

    with left_col:
        badge = "  `gold`" if incident["is_gold_set"] else ""
        st.subheader(f"#{incident['id']}{badge}")
        if incident["title"]:
            st.markdown(f"**{incident['title']}**")

        with st.expander("Report text", expanded=True):
            st.write(incident["report_text"])

        gold = incident.get("gold_annotations")
        if gold:
            st.markdown("---")
            st.markdown("**Gold annotations**")
            st.markdown(f"**Known:** {label_chips(gold['known_ai_technical_failure'])}")
            st.markdown(f"**Potential:** {label_chips(gold['potential_ai_technical_failure'])}")

    with right_col:
        st.subheader("Conversation")

        try:
            ann_configs = call_api("GET", "/compare/configs")
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()

        cfg_col_a, cfg_col_b, cfg_col_c = st.columns(3)
        with cfg_col_a:
            ann_model = st.selectbox("Model", ann_configs["models"], key="ann_model")
        with cfg_col_b:
            ann_prompt_versions = ann_configs["prompt_versions"]
            if ann_prompt_versions:
                ann_prompt = st.selectbox("Prompt version", ann_prompt_versions, key="ann_prompt")
            else:
                st.caption("No prompt versions in DB yet — will use default.")
                ann_prompt = None
        with cfg_col_c:
            ann_temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.1, key="ann_temperature")

        run_btn = st.button("Run prediction", type="primary")

        try:
            system_prompt = call_api("GET", "/system-prompt")["system_prompt"]
        except RuntimeError:
            system_prompt = None

        with st.chat_message("system"):
            st.caption("System prompt")
            if system_prompt:
                st.write(system_prompt)
            else:
                st.warning("Could not load system prompt.")

        for msg in conversation:
            if msg["kind"] == "prediction_user":
                with st.chat_message("user"):
                    st.code(msg["content"], language=None)

            elif msg["kind"] == "prediction_assistant":
                with st.chat_message("assistant"):
                    run = msg["result"]["model_run"]
                    pred = msg["result"]["prediction"]
                    meta_parts = [f"`{run['model_name']}`", f"prompt `{run['prompt_version']}`"]
                    if run["temperature"] is not None:
                        meta_parts.append(f"T={run['temperature']}")
                    if run["latency_ms"] is not None:
                        meta_parts.append(f"{run['latency_ms']} ms")
                    if run["input_tokens"] is not None and run["output_tokens"] is not None:
                        meta_parts.append(f"{run['input_tokens']}↑ {run['output_tokens']}↓ tok")
                    st.caption("  ·  ".join(meta_parts))
                    st.markdown(f"**Known:** {label_chips(pred['known_ai_technical_failure'])}")
                    st.markdown(f"**Potential:** {label_chips(pred['potential_ai_technical_failure'])}")

            elif msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])

            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])

        if run_btn:
            with st.spinner("Running prediction…"):
                try:
                    predict_params = {"model_name": ann_model, "temperature": ann_temperature}
                    if ann_prompt:
                        predict_params["prompt_version"] = ann_prompt
                    result = call_api("POST", f"/predict/{selected_id}", params=predict_params)
                    conversation = st.session_state["conversations"].get(selected_id, [])
                    conversation.append({
                        "role": "user",
                        "kind": "prediction_user",
                        "content": format_incident_prompt(incident),
                    })
                    conversation.append({
                        "role": "assistant",
                        "kind": "prediction_assistant",
                        "result": result,
                    })
                    st.session_state["conversations"][selected_id] = conversation
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

        chat_input = st.chat_input("Ask a follow-up question…")
        if chat_input:
            user_msg = chat_input.strip()
            conversation = st.session_state["conversations"].get(selected_id, [])
            history = build_chat_history(conversation)
            with st.spinner("Thinking…"):
                try:
                    response = call_api(
                        "POST",
                        f"/chat/{selected_id}",
                        body={"message": user_msg, "history": history},
                    )
                    conversation.append({"role": "user", "kind": "chat", "content": user_msg})
                    conversation.append({"role": "assistant", "kind": "chat", "content": response["content"]})
                    st.session_state["conversations"][selected_id] = conversation
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

# ══════════════════════════════════════════════════════════════════════════════
# COMPARE TAB
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    import pandas as pd

    st.subheader("Comparative Analysis")
    st.caption("Micro-averaged precision, recall, and F1 across all gold incidents. Each run adds a row to the table below.")

    try:
        configs = call_api("GET", "/compare/configs")
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    cmp_col_a, cmp_col_b, cmp_col_c = st.columns(3)
    with cmp_col_a:
        cmp_model = st.selectbox("Model name", configs["models"], key="cmp_model")
    with cmp_col_b:
        prompt_versions = configs["prompt_versions"]
        if prompt_versions:
            cmp_prompt = st.selectbox("Prompt version", prompt_versions, key="cmp_prompt")
        else:
            st.info("No model runs found in the database yet.")
            cmp_prompt = None
    with cmp_col_c:
        temperatures = configs["temperatures"]
        temp_options = ["(any)"] + [str(t) for t in temperatures]
        cmp_temp_str = st.selectbox("Temperature", temp_options, key="cmp_temp")
        cmp_temp = None if cmp_temp_str == "(any)" else float(cmp_temp_str)

    cmp_notes = st.text_input("Notes (optional)", placeholder="e.g. few-shot prompting, higher temperature test…", key="cmp_notes")

    run_col, clear_col = st.columns([3, 1])
    with run_col:
        run_cmp_btn = st.button("Add to comparison table", type="primary")
    with clear_col:
        if st.button("Clear table"):
            st.session_state["compare_rows"] = []
            st.rerun()

    if "compare_rows" not in st.session_state:
        st.session_state["compare_rows"] = []

    if run_cmp_btn:
        if not cmp_prompt:
            st.warning("No prompt versions available.")
        else:
            with st.spinner("Computing metrics…"):
                try:
                    params = {"model_name": cmp_model, "prompt_version": cmp_prompt}
                    if cmp_temp is not None:
                        params["temperature"] = cmp_temp
                    result = call_api("GET", "/compare", params=params)

                    known = result["known_ai_technical_failure"]
                    potential = result["potential_ai_technical_failure"]
                    covered_n = result["covered_incident_count"]
                    gold_n = result["gold_incident_count"]

                    st.session_state["compare_rows"].append({
                        "Model": result["model_name"],
                        "Prompt": result["prompt_version"],
                        "Temp": cmp_temp_str,
                        "Coverage": f"{covered_n}/{gold_n}",
                        "Known P": known["precision"],
                        "Known R": known["recall"],
                        "Known F1": known["f1"],
                        "Potential P": potential["precision"],
                        "Potential R": potential["recall"],
                        "Potential F1": potential["f1"],
                        "Avg In Tok": result["avg_input_tokens"] or "—",
                        "Avg Out Tok": result["avg_output_tokens"] or "—",
                        "Notes": cmp_notes or "",
                    })
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    if st.session_state["compare_rows"]:
        df = pd.DataFrame(st.session_state["compare_rows"])
        float_cols = ["Known P", "Known R", "Known F1", "Potential P", "Potential R", "Potential F1"]
        st.dataframe(
            df.style.format({col: "{:.4f}" for col in float_cols}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No comparisons yet. Configure and click 'Add to comparison table'.")
