import requests
import streamlit as st


BACKEND_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="PolicyTrace EDU",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown(
    """
    <style>
        .stApp {
            background:
                linear-gradient(
                    180deg,
                    #f7f6f2 0%,
                    #ffffff 42%
                );
        }

        .block-container {
            max-width: 1080px;
            padding-top: 2.8rem;
            padding-bottom: 4rem;
        }

        .academic-label {
            color: #92733f;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.16rem;
            margin-bottom: 0.55rem;
        }

        .academic-title {
            color: #173b63;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 3.2rem;
            font-weight: 700;
            line-height: 1.08;
        }

        .academic-title span {
            color: #92733f;
        }

        .subtitle {
            color: #607086;
            font-size: 1.05rem;
            line-height: 1.6;
            max-width: 720px;
            margin-top: 0.8rem;
            margin-bottom: 2.2rem;
        }

        .section-label {
            color: #173b63;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.65rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .section-description {
            color: #718096;
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }

        .status-success {
            padding: 0.9rem 1rem;
            border: 1px solid #b6d1c2;
            border-radius: 0.65rem;
            background-color: #eff8f3;
            color: #285942;
            margin-bottom: 1rem;
        }

        .status-error {
            padding: 0.9rem 1rem;
            border: 1px solid #dfb5b5;
            border-radius: 0.65rem;
            background-color: #fff4f4;
            color: #8b3131;
            margin-bottom: 1rem;
        }

        .privacy-note {
            padding: 0.85rem 1rem;
            border-left: 3px solid #92733f;
            background-color: #f8f4ea;
            color: #5f5544;
            font-size: 0.88rem;
            line-height: 1.5;
            margin-top: 1rem;
        }

        div[data-testid="stForm"] {
            background-color: #ffffff;
            border: 1px solid #d8dee8;
            border-radius: 0.85rem;
            padding: 1.35rem;
            box-shadow: 0 8px 25px rgba(23, 59, 99, 0.06);
        }

        div[data-testid="stSidebar"] {
            background-color: #edf1f5;
            border-right: 1px solid #d6dde7;
        }

        div[data-testid="stSidebar"] h2,
        div[data-testid="stSidebar"] h3 {
            color: #173b63;
            font-family: Georgia, "Times New Roman", serif;
        }

        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #d8dee8;
            border-radius: 0.7rem;
            padding: 0.75rem;
        }

        .stFormSubmitButton > button {
            background-color: #1f4e79;
            border: 1px solid #1f4e79;
            border-radius: 0.5rem;
            color: #ffffff;
            font-weight: 600;
        }

        .stFormSubmitButton > button:hover {
            background-color: #173b63;
            border-color: #173b63;
            color: #ffffff;
        }

        div[data-testid="stExpander"] {
            border: 1px solid #d8dee8;
            border-radius: 0.65rem;
            background-color: #ffffff;
        }

        #MainMenu,
        footer,
        div[data-testid="stToolbar"] {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True
)


def get_backend_health():
    """Check whether the local inference backend is ready."""

    try:
        response = requests.get(
            f"{BACKEND_URL}/health",
            timeout=5
        )

        if response.ok:
            return response.json()

    except requests.RequestException:
        return None

    return None


def request_analysis(question, role, top_k):
    """Send a policy question to the local backend."""

    response = requests.post(
        f"{BACKEND_URL}/analyze",
        json={
            "question": question,
            "role": role,
            "top_k": top_k
        },
        timeout=900
    )

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "The local backend returned an invalid response."
        )

    if not response.ok:
        raise RuntimeError(
            data.get("error", "Unknown backend error.")
        )

    return data


health = get_backend_health()


st.markdown(
    """
    <div class="academic-label">
        ACADEMIC POLICY INTELLIGENCE
    </div>

    <div class="academic-title">
        PolicyTrace <span>EDU</span>
    </div>

    <div class="subtitle">
        A version-aware institutional memory assistant that
        helps students and academic staff identify applicable
        university policies, supporting evidence and unresolved
        policy conflicts.
    </div>
    """,
    unsafe_allow_html=True
)


with st.sidebar:
    st.header("System")

    if health:
        st.markdown(
            """
            <div class="status-success">
                ● Local policy engine connected<br>
                Private on-device inference
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            f"**Chat model**  \n"
            f"{health.get('chat_model', 'Phi-4 Mini')}"
        )

        st.write(
            f"**Embedding model**  \n"
            f"{health.get('embedding_model', 'Qwen3 Embedding')}"
        )

        st.metric(
            "Indexed policy sections",
            health.get("indexed_chunks", 0)
        )

    else:
        st.markdown(
            """
            <div class="status-error">
                ● Local policy engine unavailable
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(
            "Start backend.py in a separate "
            "PowerShell window."
        )

    st.divider()

    st.subheader("Privacy")

    st.markdown(
        """
        <div class="privacy-note">
            Policy documents, questions and model responses
            remain on this device. No cloud inference API
            is used.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.caption(
        "Prototype developed with Microsoft Foundry Local."
    )


st.markdown(
    """
    <div class="section-label">
        Ask a policy question
    </div>

    <div class="section-description">
        Select your academic role and ask which policy,
        version or procedure applies.
    </div>
    """,
    unsafe_allow_html=True
)


default_question = (
    "The older exchange guide and the current academic "
    "policy describe different approval steps. Which "
    "procedure should a student follow, and what evidence "
    "supports the answer?"
)


with st.form("policy_analysis_form"):
    first_column, second_column = st.columns([2, 1])

    with first_column:
        role = st.selectbox(
            "Academic role",
            [
                "Student",
                "Academic Advisor",
                "Department Administrator"
            ]
        )

    with second_column:
        top_k = st.selectbox(
            "Evidence sections",
            [2, 3, 4],
            index=1
        )

    question = st.text_area(
        "Policy or procedure question",
        value=default_question,
        height=145,
        placeholder=(
            "Ask about exchange recognition, "
            "academic procedures or policy versions..."
        )
    )

    analyze_button = st.form_submit_button(
        "Review applicable policies",
        type="primary",
        width="stretch"
    )


if analyze_button:
    if not health:
        st.error(
            "The local backend is not running. "
            "Start backend.py first."
        )

    elif not question.strip():
        st.warning("Please enter a policy question.")

    else:
        with st.spinner(
            "Reviewing policy versions and retrieved evidence..."
        ):
            try:
                result = request_analysis(
                    question=question,
                    role=role,
                    top_k=top_k
                )

            except requests.Timeout:
                st.error(
                    "The local model exceeded the response timeout."
                )
                st.stop()

            except requests.ConnectionError:
                st.error(
                    "The connection to the local backend was lost."
                )
                st.stop()

            except Exception as error:
                st.error(f"Analysis failed: {error}")
                st.stop()

        st.divider()

        st.markdown(
            """
            <div class="section-label">
                Policy guidance
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(result["answer"])

        response_time = result.get(
            "response_time_seconds"
        )

        if response_time is not None:
            st.caption(
                f"Generated locally in "
                f"{response_time} seconds."
            )

        st.divider()

        st.markdown(
            """
            <div class="section-label">
                Evidence trace
            </div>

            <div class="section-description">
                Retrieved policy sections used to construct
                the response.
            </div>
            """,
            unsafe_allow_html=True
        )

        for index, source in enumerate(
            result.get("sources", []),
            start=1
        ):
            score = source.get("score", 0.0)
            progress_value = max(
                0.0,
                min(1.0, score)
            )

            source_name = source.get(
                "source",
                "Unknown policy"
            )

            label = (
                f"{index}. {source_name} "
                f"— relevance {score:.4f}"
            )

            with st.expander(label):
                st.progress(progress_value)

                st.caption(
                    f"Section "
                    f"{source.get('chunk_index', 0)} · "
                    f"Semantic relevance {score:.4f}"
                )

                st.write(
                    source.get(
                        "content",
                        "No policy text available."
                    )
                )


st.divider()

st.caption(
    "PolicyTrace EDU is a research prototype. Its responses "
    "must be verified against official university sources and "
    "do not replace authorized academic or administrative guidance."
)