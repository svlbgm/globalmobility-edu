import traceback
import streamlit as st

from src.database import get_chunk_count
from src.rag_pipeline import RAGPipeline


st.set_page_config(
    page_title="CrisisLens Local",
    page_icon="🛡️",
    layout="wide"
)


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1100px;
            padding-top: 2rem;
        }

        .status-card {
            padding: 0.8rem 1rem;
            border: 1px solid #B7E4C7;
            border-radius: 0.7rem;
            background: #F0FFF4;
            color: #175C35;
            margin-bottom: 1rem;
        }

        .hero-subtitle {
            color: #667085;
            font-size: 1.05rem;
            margin-bottom: 1.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)


@st.cache_resource(show_spinner=False)
def load_pipeline():
    """Load and cache the local AI models."""

    pipeline = RAGPipeline()
    pipeline.start()

    return pipeline


st.title("🛡️ CrisisLens Local")

st.markdown(
    """
    <div class="hero-subtitle">
        Private, offline and evidence-grounded operational
        crisis assistance
    </div>
    """,
    unsafe_allow_html=True
)


with st.sidebar:
    st.header("System status")

    st.markdown(
        """
        <div class="status-card">
            ● Local processing enabled<br>
            No cloud API or external inference
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("**Chat model:** Phi-4 Mini")
    st.write("**Embedding model:** Qwen3 Embedding")
    st.write(f"**Indexed evidence:** {get_chunk_count()} chunks")

    st.divider()

    st.header("Response settings")

    role = st.selectbox(
        "Organizational role",
        [
            "Operations Manager",
            "IT Lead",
            "Employee",
            "Incident Commander",
            "Communications Lead"
        ]
    )

    top_k = st.slider(
        "Evidence chunks",
        min_value=2,
        max_value=4,
        value=4,
        help=(
            "Number of document chunks supplied "
            "to the local language model."
        )
    )


scenario_questions = {
    "Ransomware response": (
        "Several employee computers appear to be locked "
        "by ransomware. What should I do during the first "
        "30 minutes, and should the affected computers "
        "be powered off?"
    ),
    "External communication": (
        "A journalist has contacted an employee about "
        "the incident. What information can the employee "
        "share and who should respond?"
    ),
    "Extended disruption": (
        "Critical systems may remain unavailable for more "
        "than four hours. What continuity actions and "
        "records are required?"
    ),
    "Missing information test": (
        "What is the emergency cybersecurity phone number?"
    )
}


st.subheader("Incident analysis")

selected_scenario = st.selectbox(
    "Example scenario",
    list(scenario_questions.keys())
)

question = st.text_area(
    "Describe the incident or ask a question",
    value=scenario_questions[selected_scenario],
    height=140
)


if st.button(
    "Analyze incident",
    type="primary",
    width="stretch"
):
    if not question.strip():
        st.warning("Please describe an incident or question.")

    else:
        with st.spinner(
            "Loading local models and analyzing evidence..."
        ):
            try:
                pipeline = load_pipeline()

                result = pipeline.answer(
                    question=question,
                    role=role,
                    top_k=top_k
                )

            except Exception as error:
                error_details = traceback.format_exc()

                print(error_details)

                st.error(f"Analysis failed: {error}")

                with st.expander("Technical error details"):
                    st.code(error_details)

                st.stop()

        st.divider()

        st.subheader("Grounded response")
        st.markdown(result["answer"])

        st.divider()

        st.subheader("Retrieved evidence")

        for index, source in enumerate(
            result["sources"],
            start=1
        ):
            score = source["score"]
            progress_value = max(0.0, min(1.0, score))

            label = (
                f"{index}. {source['source']} "
                f"— relevance {score:.4f}"
            )

            with st.expander(label):
                st.progress(progress_value)

                st.caption(
                    f"Chunk {source['chunk_index']} · "
                    f"Semantic relevance {score:.4f}"
                )

                st.write(source["content"])


st.divider()

st.caption(
    "CrisisLens Local is a demonstration system using "
    "synthetic documents. It does not replace authorized "
    "emergency, cybersecurity, legal or safety professionals."
)