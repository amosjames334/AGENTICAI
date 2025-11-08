# Example inside agents/research_graph.py or agents/agent_definitions.py (where retrieval happens)
from src.ingestion.document_processor import DocumentProcessor

def retrieve_evidence(query: str, k: int = 5):
    dp = DocumentProcessor("data")
    return dp.query(query, k=k)

# then in your ResearchAgent:
hits = retrieve_evidence(user_question, k=5)
evidence_snippets = [h["text"] for h in hits]
# pass evidence_snippets downstream instead of titles/abstracts
