from datetime import datetime, timedelta
import streamlit as st
from agents.model_manager import ModelManager
from parsers.medical_value_extractor import extract_values

class AnalysisAgent:
    def __init__(self):
        self.model_manager = ModelManager()
        self._init_state()

    # ---------------- STATE ----------------
    def _init_state(self):
        if "analysis_count" not in st.session_state:
            st.session_state.analysis_count = 0
        if "last_analysis" not in st.session_state:
            st.session_state.last_analysis = datetime.now()
        if "analysis_limit" not in st.session_state:
            st.session_state.analysis_limit = 15
        if "models_used" not in st.session_state:
            st.session_state.models_used = {}
        if "knowledge_base" not in st.session_state:
            st.session_state.knowledge_base = {}

    # ---------------- RATE LIMIT ----------------
    def check_rate_limit(self):
        time_until_reset = timedelta(days=1) - (
            datetime.now() - st.session_state.last_analysis
        )

        hours, remainder = divmod(time_until_reset.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if time_until_reset.days < 0:
            st.session_state.analysis_count = 0
            st.session_state.last_analysis = datetime.now()
            return True, None

        if st.session_state.analysis_count >= st.session_state.analysis_limit:
            return False, f"Daily limit reached. Reset in {hours}h {minutes}m"

        return True, None

    # ---------------- MAIN PIPELINE ----------------
    def analyze_report(self, data, system_prompt, check_only=False, chat_history=None):
        can_analyze, error_msg = self.check_rate_limit()

        if not can_analyze:
            return {"success": False, "error": error_msg}

        if check_only:
            return can_analyze, error_msg

        processed_data = self._preprocess_data(data)

        # Safety guard — previously blocked analysis, now just warns if values are missing
        if isinstance(processed_data, dict) and not processed_data.get("lab_values"):
            # We allow analysis to proceed but add a warning to the system prompt
            system_prompt += "\n\nNOTE: Structured medical values were not detected. Please analyze the raw text carefully and provide insights based on available information."

        enhanced_prompt = (
            self._build_enhanced_prompt(system_prompt, processed_data, chat_history)
            if chat_history
            else system_prompt
        )

        result = self.model_manager.generate_analysis(processed_data, enhanced_prompt)

        if result.get("success"):
            self._update_analytics(result)
            self._update_knowledge_base(processed_data, result.get("content", ""))

        return result

    # ---------------- PREPROCESS ----------------
    def _preprocess_data(self, data):
        if not isinstance(data, dict):
            return data

        report_text = data.get("report", "")

        extracted_values = extract_values(report_text)

        return {
            "patient_name": data.get("patient_name", ""),
            "age": data.get("age", ""),
            "gender": data.get("gender", ""),
            "report": report_text,
            "lab_values": extracted_values,
        }

    # ---------------- ANALYTICS ----------------
    def _update_analytics(self, result):
        st.session_state.analysis_count += 1
        st.session_state.last_analysis = datetime.now()

        model_used = result.get("model_used", "unknown")
        st.session_state.models_used[model_used] = (
            st.session_state.models_used.get(model_used, 0) + 1
        )

    # ---------------- MEMORY LEARNING ----------------
    def _update_knowledge_base(self, data, analysis):
        if not isinstance(data, dict) or "report" not in data:
            return

        report_text = data["report"].lower()
        patient_profile = f"{data.get('age','unknown')}-{data.get('gender','unknown')}"

        indicators = [
            "hemoglobin",
            "glucose",
            "cholesterol",
            "triglycerides",
            "hdl",
            "ldl",
            "wbc",
            "rbc",
            "platelet",
            "creatinine",
        ]

        for indicator in indicators:
            if indicator in report_text and indicator in analysis.lower():

                kb = st.session_state.knowledge_base.setdefault(indicator, {})
                history = kb.setdefault(patient_profile, [])

                line = next(
                    (l for l in analysis.split("\n") if indicator in l.lower()), None
                )

                if line:
                    if len(history) >= 3:
                        history.pop(0)
                    history.append(line)

    # ---------------- PROMPT ENHANCEMENT ----------------
    def _build_enhanced_prompt(self, system_prompt, data, chat_history):
        prompt = system_prompt

        kb_context = self._get_knowledge_base_context(data)
        if kb_context:
            prompt += "\n\n## Relevant Learning From Previous Analyses\n" + kb_context

        session_context = self._get_session_context(chat_history)
        if session_context:
            prompt += "\n\n## Current Session History\n" + session_context

        return prompt

    def _get_knowledge_base_context(self, data):
        if not st.session_state.knowledge_base:
            return ""

        report_text = data.get("report", "").lower()
        context = []

        for indicator, profiles in st.session_state.knowledge_base.items():
            if indicator in report_text:
                for insights in profiles.values():
                    context.extend(f"- {indicator}: {i}" for i in insights)

        return "\n".join(context[:5])

    def _get_session_context(self, chat_history):
        if not chat_history or len(chat_history) < 2:
            return ""

        context = []
        for i in range(len(chat_history) - 1, 0, -2):
            if (
                chat_history[i - 1]["role"] == "user"
                and chat_history[i]["role"] == "assistant"
            ):
                u = chat_history[i - 1]["content"][:200]
                a = chat_history[i]["content"][:200]
                context.append(f"User: {u}\nAssistant: {a}")
                if len(context) >= 2:
                    break

        return "\n\n".join(reversed(context))