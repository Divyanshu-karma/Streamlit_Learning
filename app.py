import os
import json
import streamlit as st
import pdfplumber
import requests


# =================================
# PAGE CONFIG
# =================================

st.set_page_config(
    page_title="Trademark Risk Assessment Engine",
    layout="wide"
)

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
BACKEND_URL = st.secrets["BACKEND_URL"]


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# =================================
# FORCE DARK THEME
# =================================

bg = "#0b1220"
card = "#1e293b"
inner_card = "#243244"
text = "#f1f5f9"
border = "#334155"

# =================================
# GLOBAL DARK STYLING
# =================================

st.markdown(f"""
<style>

header {{visibility:hidden;}}
footer {{visibility:hidden;}}

html, body, [data-testid="stAppViewContainer"] {{
    background-color: {bg} !important;
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}}

.section-card {{
    background: {card};
    padding: 30px;
    border-radius: 16px;
    border: 1px solid {border};
    margin-bottom: 30px;
}}

[data-testid="column"] > div {{
    background: transparent !important;
}}

h1, h2, h3, h4, h5, h6, p, label {{
    color: {text} !important;
}}

[data-testid="stFileUploader"] > div {{
    background: {inner_card} !important;
    border-radius: 12px;
    border: 1px solid {border};
    padding: 12px;
}}

.pipeline-container {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}}

.pipeline-box {{
    flex: 1;
    padding: 20px;
    text-align: center;
    border-radius: 14px;
    border: 1px solid {border};
    background: {inner_card};
    font-weight: 600;
}}

.pipeline-arrow {{
    font-size: 22px;
    font-weight: bold;
    color: {text};
}}

button {{
    border-radius: 8px !important;
}}

</style>
""", unsafe_allow_html=True)

# =================================
# HEADER
# =================================

st.markdown("""
<div class="section-card">
<h2 style="margin-bottom:8px;">Trademark Risk Assessment Engine</h2>
<p style="opacity:0.65;">
Retrieval-Augmented Legal Analysis (TMEP-Grounded)
</p>
</div>
""", unsafe_allow_html=True)

# =================================
# PIPELINE FLOW
# =================================

st.markdown(f"""
<div class="section-card">
<div class="pipeline-container">

<div class="pipeline-box">
Upload Your<br>Trademark Document
</div>

<div class="pipeline-arrow">→</div>

<div class="pipeline-box">
Extracting<br>Information
</div>

<div class="pipeline-arrow">→</div>

<div class="pipeline-box">
RAG Pipeline<br>Processing
</div>

<div class="pipeline-arrow">→</div>

<div class="pipeline-box">
Risk-Categorized<br>Assessment
</div>

</div>
</div>
""", unsafe_allow_html=True)

# =================================
# HELPER: JSON TO TEXT
# =================================

def format_json_to_text(data, indent=0):
    text_output = ""
    spacing = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            text_output += f"{spacing}{key}:\n"
            text_output += format_json_to_text(value, indent + 1)
    elif isinstance(data, list):
        for i, item in enumerate(data, 1):
            text_output += f"{spacing}- Item {i}:\n"
            text_output += format_json_to_text(item, indent + 1)
    else:
        text_output += f"{spacing}{data}\n"

    return text_output

# =================================
# FUNCTIONS
# =================================

def extract_text_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except:
        return None


def call_groq_llm(raw_text):

    system_prompt = f"""
Return ONLY valid JSON.

STRUCTURE:
{{
  "mark_info": {{"literal":"","type":"","register":""}},
  "filing_basis": {{"basis_type":"","use_in_commerce":null}},
  "goods_and_services":[{{"class_id":"","description":""}}],
  "owner": {{"name":"","entity":"","citizenship":""}},
  "identifiers": {{"serial_number":"","registration_number":""}}
}}

DOCUMENT:
{raw_text}
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_prompt}],
        "temperature": 0.1
    }

    response = requests.post(GROQ_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return None

    return response.json()["choices"][0]["message"]["content"]

# =================================
# MAIN LAYOUT
# =================================

left, right = st.columns([1, 2])

# LEFT PANEL
with left:

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Upload Trademark Application")

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file:
        raw_text = extract_text_from_pdf(uploaded_file)

        if raw_text:
            if st.button("Generate Structured JSON"):
                with st.spinner("Extracting structured data..."):
                    llm_output = call_groq_llm(raw_text)

                    if llm_output:
                        try:
                            parsed = json.loads(llm_output)
                            st.session_state["parsed_json"] = parsed
                            st.success("JSON generated successfully.")
                        except:
                            st.error("Invalid JSON returned.")

    st.markdown('</div>', unsafe_allow_html=True)

# RIGHT PANEL
with right:

    if "parsed_json" in st.session_state:

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Structured JSON")
        st.json(st.session_state["parsed_json"])

        if st.button("Run Risk Analysis"):

            loading_placeholder = st.empty()
            loading_placeholder.markdown("### ⏳ Loading...")

            try:
                

                response = requests.post(
                    BACKEND_URL,

                    json={"data": st.session_state["parsed_json"]},
                    timeout=500
                )

                if response.status_code == 200:
                    st.session_state["risk"] = response.json()
                else:
                    st.error(f"Backend error {response.status_code}: {response.text}")

            except Exception as e:
                st.error(f"Connection error: {str(e)}")

            loading_placeholder.empty()

        st.markdown('</div>', unsafe_allow_html=True)

    if "risk" in st.session_state:

        st.markdown("<div id='risk_output'></div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Risk Assessment Output")

        formatted_text = format_json_to_text(st.session_state["risk"])
        st.text(formatted_text)
        st.markdown(
            """
            <meta http-equiv="refresh" content="0; URL=#risk_output">
            """,
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        
