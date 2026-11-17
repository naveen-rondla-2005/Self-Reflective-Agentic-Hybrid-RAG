import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from core.config import Config
from core.state import AgentState
from core.retriever import HybridTransitRetriever

class DocDeclutterAgent:
    def __init__(self, retriever: HybridTransitRetriever):
        Config.validate()
        self.retriever = retriever
        self.llm = ChatGoogleGenerativeAI(
            model=Config.LLM_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.0,
            thinking_budget=0,
            max_retries=2,
            timeout=60
        )
        self.graph = self._build_graph()

    def _extract_text(self, content) -> str:
        if isinstance(content, list):
            return "".join(
                block.get("text", "") for block in content if isinstance(block, dict) and "text" in block
            )
        return str(content)

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("router", self.route_query)
        workflow.add_node("retrieve", self.retrieve_documents)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("generate_answer", self.generate_answer)
        workflow.add_node("generate_summary", self.generate_summary)

        workflow.set_entry_point("router")

        workflow.add_conditional_edges(
            "router",
            lambda state: "generate_summary" if state["summary_mode"] else "retrieve",
            {
                "generate_summary": "retrieve",
                "retrieve": "retrieve"
            }
        )

        workflow.add_edge("retrieve", "grade_documents")

        workflow.add_conditional_edges(
            "grade_documents",
            lambda state: "generate_summary" if state["summary_mode"] else ("generate_answer" if state["is_relevant"] else "insufficient_info"),
            {
                "generate_summary": "generate_summary",
                "generate_answer": "generate_answer",
                "insufficient_info": END
            }
        )

        workflow.add_edge("generate_answer", END)
        workflow.add_edge("generate_summary", END)

        return workflow.compile()

    def route_query(self, state: AgentState):
        print("[1/4] Routing query intent...")
        query = state["query"].lower()
        summary_keywords = ["summarize", "summary", "overview", "protocol", "workflow", "highlights", "brief"]
        summary_mode = any(word in query for word in summary_keywords)
        return {"summary_mode": summary_mode, "documents": []}

    def retrieve_documents(self, state: AgentState):
        print("[2/4] Executing Hybrid Search (ChromaDB + BM25 + RRF)...")
        query = state["query"]
        docs = self.retriever.retrieve(query)
        return {"documents": docs}

    def grade_documents(self, state: AgentState):
        print("[3/4] Grading retrieved document chunks for grounding...")
        docs = state.get("documents", [])
        if not docs:
            return {"is_relevant": False, "response": "No operational documents matched the search criteria."}

        context = "\n---\n".join([d.page_content[:600] for d in docs])
        prompt = PromptTemplate(
            template="""You are an AI auditor for Kochi Metro.
Determine if the provided document extracts contain relevant factual information to answer all or part of this query:
Query: {query}
Extracts: {context}

Respond strictly with valid JSON: {{"relevant": true}} or {{"relevant": false}}
""",
            input_variables=["query", "context"]
        )
        chain = prompt | self.llm
        evaluation = chain.invoke({"query": state["query"], "context": context})

        try:
            raw_eval = self._extract_text(evaluation.content)
            cleaned = raw_eval.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned)
            is_rel = data.get("relevant", True)
        except Exception:
            is_rel = True

        response_msg = ""
        if not is_rel and not state["summary_mode"]:
            response_msg = "The ingested KMRL documents do not contain direct operational information on this matter. Please consult the safety head or operations supervisor."

        return {"is_relevant": is_rel, "response": response_msg}

    def generate_answer(self, state: AgentState):
        print("[4/4] Synthesizing grounded operational response...")
        docs = state["documents"]
        context_blocks = []
        citations = []

        for doc in docs:
            src = doc.metadata.get("source_name", "Unknown Document")
            page = doc.metadata.get("page", 0) + 1
            context_blocks.append(f"[{src} - Page {page}]\n{doc.page_content[:650]}")
            citations.append({
                "source": src,
                "page": page,
                "snippet": doc.page_content[:180] + "..."
            })

        context_str = "\n\n".join(context_blocks)
        prompt = PromptTemplate(
            template="""You are KMRL DocDeclutter AI, an operational expert assistant for Kochi Metro Rail Limited.
Answer the operational inquiry below based solely on the provided extracts.
Use clear, technical bullet points and cite the source and page number in brackets for each fact.

Operational Documents:
{context}

Query: {query}

Answer:""",
            input_variables=["context", "query"]
        )
        chain = prompt | self.llm
        output = chain.invoke({"context": context_str, "query": state["query"]})

        return {"response": self._extract_text(output.content), "citations": citations}

    def generate_summary(self, state: AgentState):
        print("[4/4] Synthesizing executive summary...")
        docs = state["documents"]
        combined_text = "\n\n".join([f"[{d.metadata.get('source_name', 'Doc')} P.{d.metadata.get('page', 0)+1}]: {d.page_content[:650]}" for d in docs])

        prompt = PromptTemplate(
            template="""You are KMRL DocDeclutter AI.
Provide an executive operational summary for metro leadership based on the following document sections:

Sections:
{context}

Topic to summarize: {query}

Structure your response with:
1. Executive Overview
2. Key Operational Protocols / Directives
3. Source Document Reference Table
""",
            input_variables=["context", "query"]
        )
        chain = prompt | self.llm
        output = chain.invoke({"context": combined_text, "query": state["query"]})

        citations = [{
            "source": d.metadata.get("source_name", "Doc"),
            "page": d.metadata.get("page", 0) + 1,
            "snippet": d.page_content[:150] + "..."
        } for d in docs]

        return {"response": self._extract_text(output.content), "citations": citations}

    def run(self, query: str) -> AgentState:
        initial_state: AgentState = {
            "query": query,
            "intent": "",
            "documents": [],
            "is_relevant": False,
            "summary_mode": False,
            "response": "",
            "citations": []
        }
        return self.graph.invoke(initial_state)