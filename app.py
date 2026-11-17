import os
import streamlit as st
from core.config import Config
from core.retriever import HybridTransitRetriever
from core.graph import DocDeclutterAgent

st.set_page_config(
    page_title="KMRL DocDeclutter | Agentic AI Transit Hub",
    page_icon="🚇",
    layout="wide"
)

@st.cache_resource
def load_system():
    retriever = HybridTransitRetriever()
    retriever.initialize()
    agent = DocDeclutterAgent(retriever)
    return retriever, agent

retriever, agent = load_system()

st.markdown("""
    <div style="background-color:#0e2a47;padding:18px;border-radius:10px;margin-bottom:20px;">
        <h2 style="color:white;margin:0;">🚇 DocDeclutter: KMRL Metro Document Automation</h2>
        <p style="color:#b0c4de;margin:4px 0 0 0;">Agentic RAG Engine with Hybrid Search & Automated Citation Verification</p>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Transit Document Hub")
    st.caption("Batch ingest unstructured transit operational guidelines, logs, & circulars.")

    uploaded_files = st.file_uploader("Upload Transit PDFs", type=["pdf"], accept_multiple_files=True)
    if st.button("Ingest & Re-Index", use_container_width=True):
        if uploaded_files:
            os.makedirs(Config.DOCS_DIR, exist_ok=True)
            for file in uploaded_files:
                target_path = os.path.join(Config.DOCS_DIR, file.name)
                with open(target_path, "wb") as f:
                    f.write(file.getbuffer())
            with st.spinner("Processing text chunks & calculating hybrid vectors..."):
                retriever.reindex_corpus()
            st.success(f"Indexed {len(uploaded_files)} files into ChromaDB + BM25!")
        else:
            st.warning("Please attach files to upload.")

    st.markdown("---")
    st.markdown("### 📋 Currently Ingested Files")
    if os.path.exists(Config.DOCS_DIR):
        existing_docs = [f for f in os.listdir(Config.DOCS_DIR) if f.endswith(".pdf")]
        if existing_docs:
            for doc in existing_docs:
                st.markdown(f"- 📄 `{doc}`")
        else:
            st.info("No documents currently loaded.")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Operational Query Console")
    sample_queries = [
    "How many total train trips did KMRL operate in FY 2024-25, what was the fare box revenue, and how many trains were in operation?",
    "What is the operating surplus and ridership achieved by KMRL in FY 2024-25?",
    "Summarize the security measures, surveillance systems, and mock drills conducted by KMRL across stations and depots.",
    "What is the ticket fare from Aluva to Pettah for the Kochi Metro Phase 3 underwater tunnel?"
    ]
    selected_sample = st.selectbox("Or choose a pre-formulated operational test query:", [""] + sample_queries)
    
    user_query = st.text_input("Enter your query:", value=selected_sample)

    if st.button("Execute Agent Analysis", type="primary") and user_query:
        with st.spinner("Agent routing, retrieving, and evaluating document validity..."):
            result = agent.run(user_query)

        st.markdown("### Operational Assessment & Response")
        st.markdown(result["response"])

        if result.get("citations"):
            st.markdown("---")
            st.markdown("#### 🔍 Verifiable Document Grounding & Citations")
            for idx, cit in enumerate(result["citations"]):
                with st.expander(f"Citation [{idx+1}]: {cit['source']} (Page {cit['page']})"):
                    st.info(f"Matched Excerpt:\n\"{cit['snippet']}\"")

with col2:
    st.subheader("System Architecture")
    st.markdown("""
    **Evaluation Highlights:**
    - **Hybrid Search**: BM25 (keyword exact match) + Sentence-Transformers (semantic search).
    - **Self-Reflective Agent**: Built using LangGraph. Evaluates document relevance to avoid speculative hallucinations.
    - **Granular Citations**: Formats answers directly tied to source file names and page indices.
    """)