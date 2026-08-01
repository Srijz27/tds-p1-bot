"""
Exact proposal/commit schema should be copied from the assignment page.
For now, this scaffold uses a minimal stable shape.
"""


def build_proposal(evaluation_id, dossier, decision):
    return {
        "evaluation_id": evaluation_id,
        "dossier_id": dossier.get("id"),
        "decision": decision.get("type"),
        "reason": decision.get("reason"),
        "status": "pending",
    }


def apply_action(proposal, receipt):
    return {
        "proposal": proposal,
        "receipt": receipt,
        "outcome": "applied",
    }
