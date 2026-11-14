"""Memory Court: verdict proposal and human approval. See brief section 8.

The model only drafts. Nothing changes in memories until a human approves.
"""


def propose_verdict(decision_id: str) -> dict:
    # TODO: culprit from replay -> newer same-tenant evidence (vector search on evidence_vector_index,
    # or match on 'service' tag) -> llm.propose_correction -> store verdict as 'proposed'.
    raise NotImplementedError


def approve_verdict(verdict_id: str, approved_by: str) -> dict:
    # TODO: quarantine old memory; for 'correct' insert version+1 with supersedes/source_evidence_id and
    # fresh embedding; set superseded_by; mark verdict approved.
    raise NotImplementedError
