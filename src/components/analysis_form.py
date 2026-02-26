import streamlit as st
from config.prompts import SPECIALIST_PROMPTS
from utils.pdf_extractor import extract_text_from_pdf
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB


# -----------------------------
# MAIN ENTRY
# -----------------------------
def show_analysis_form():

    # Persist report text across reruns
    if "report_text" not in st.session_state:
        st.session_state.report_text = None

    report_source = st.radio(
        "Choose report source",
        ["Upload PDF", "Use Sample PDF"],
        horizontal=True,
        key="report_source",
    )

    pdf_contents = get_report_contents(report_source)

    # IMPORTANT: use session_state instead of variable
    if st.session_state.get("report_text"):
        render_patient_form(st.session_state.report_text)


# -----------------------------
# GET REPORT CONTENT
# -----------------------------
def get_report_contents(report_source):

    # keep report persistent
    if "report_text" not in st.session_state:
        st.session_state.report_text = None

    # SAMPLE REPORT MODE
    if report_source == "Use Sample PDF":
        st.session_state.report_text = SAMPLE_REPORT

        with st.expander("View Sample Report"):
            st.text(st.session_state.report_text)

        return st.session_state.report_text

    # UPLOAD MODE
    uploaded_file = st.file_uploader(
        f"Upload blood report PDF (Max {MAX_UPLOAD_SIZE_MB}MB)",
        type=["pdf"],
    )

    if uploaded_file:
        success, result = extract_text_from_pdf(uploaded_file)

        if not success:
            st.error(result)
            st.session_state.report_text = None
            return None

        st.session_state.report_text = result

        with st.expander("View Extracted Report"):
            st.text(result)

        return result

    # IMPORTANT → return stored value if exists
    return st.session_state.report_text

# -----------------------------
# FORM UI
# -----------------------------
def render_patient_form(pdf_contents):

    with st.form("analysis_form"):

        patient_name = st.text_input("Patient Name")
        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, value=30)

        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        submitted = st.form_submit_button("Analyze Report")

    if submitted:
        handle_form_submission(patient_name, age, gender, pdf_contents)


# -----------------------------
# SUBMIT HANDLER
# -----------------------------
def handle_form_submission(patient_name, age, gender, pdf_contents):

    if not patient_name:
        st.error("Enter patient name")
        return

    from services.ai_service import generate_analysis

    with st.spinner("Analyzing report..."):

        result = generate_analysis(
            {
                "patient_name": patient_name,
                "age": age,
                "gender": gender,
                "report": pdf_contents,
            },
            SPECIALIST_PROMPTS["comprehensive_analyst"],
        )

    if result.get("success"):
        st.success("Analysis Complete")

        # SAVE FOR CHAT CONTEXT
        st.session_state.current_report_text = pdf_contents

        # DISPLAY OUTPUT
        st.markdown("## 🧠 AI Medical Analysis")
        st.write(result["content"])

    else:
        st.error(result.get("error", "Analysis failed"))

