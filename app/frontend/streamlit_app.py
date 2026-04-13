import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = 30


def call_api(method: str, path: str) -> dict | list:
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=API_TIMEOUT_SECONDS,
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


def render_label_list(title: str, labels: list[str]) -> None:
    st.markdown(f"**{title}**")
    if labels:
        for label in labels:
            st.write(f"- {label}")
    else:
        st.write("No labels.")


def render_label_group(title: str, labels: dict[str, list[str]]) -> None:
    st.markdown(f"### {title}")
    known_col, potential_col = st.columns(2)

    with known_col:
        render_label_list(
            "Known AI Technical Failure",
            labels["known_ai_technical_failure"],
        )

    with potential_col:
        render_label_list(
            "Potential AI Technical Failure",
            labels["potential_ai_technical_failure"],
        )


st.set_page_config(page_title="GMF Annotation Platform", layout="wide")
st.title("GMF Annotation Platform")
st.caption(f"Backend: `{API_BASE_URL}`")

try:
    incidents = call_api("GET", "/incidents")
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.subheader("Incidents")
search_query = st.text_input(
    "Search incidents",
    placeholder="Search by incident id, title, or report text",
)

query = search_query.strip().lower()
filtered_incidents = [
    incident
    for incident in incidents
    if not query
    or query in str(incident["id"]).lower()
    or query in (incident["title"] or "").lower()
    or query in incident["report_text"].lower()
]

if not filtered_incidents:
    st.info("No incidents match the current search.")
    st.stop()

incident_labels = {
    incident["id"]: (
        f'#{incident["id"]} - {(incident["title"] or "Untitled incident")[:100]}'
        + (" [gold]" if incident["is_gold_set"] else "")
    )
    for incident in filtered_incidents
}
selected_incident_id = st.selectbox(
    "Select incident",
    [incident["id"] for incident in filtered_incidents],
    format_func=lambda incident_id: incident_labels[incident_id],
)

try:
    incident = call_api("GET", f"/incidents/{selected_incident_id}")
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

st.subheader(incident["title"] or f"Incident {incident['id']}")
st.write(f"**Incident ID:** {incident['id']}")
st.write(f"**Gold set:** {'Yes' if incident['is_gold_set'] else 'No'}")
st.text_area(
    "Report text",
    incident["report_text"],
    height=320,
    disabled=True,
)

if "prediction_results" not in st.session_state:
    st.session_state["prediction_results"] = {}

prediction_result = st.session_state["prediction_results"].get(selected_incident_id)

if st.button("Run prediction"):
    with st.spinner("Running prediction..."):
        try:
            prediction_result = call_api("POST", f"/predict/{selected_incident_id}")
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.session_state["prediction_results"][selected_incident_id] = (
                prediction_result
            )

gold_annotations = incident.get("gold_annotations")
has_gold_annotations = gold_annotations is not None

if has_gold_annotations and prediction_result:
    st.subheader("Label Comparison")
    gold_col, prediction_col = st.columns(2)

    with gold_col:
        render_label_group("Gold Annotations", gold_annotations)

    with prediction_col:
        render_label_group("Prediction", prediction_result["prediction"])
elif has_gold_annotations:
    render_label_group("Gold Annotations", gold_annotations)
elif prediction_result:
    render_label_group("Prediction", prediction_result["prediction"])

if prediction_result:
    st.subheader("Model Run")
    st.json(prediction_result["model_run"])
else:
    if has_gold_annotations:
        st.info("Run prediction to compare the model output against the gold annotations.")
    else:
        st.info("Select an incident and run prediction to see labels.")
