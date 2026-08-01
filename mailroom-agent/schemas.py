def validate_propose_request(body):
    if not isinstance(body, dict):
        return False, "body must be a JSON object"
    required = ["operation", "evaluation_id", "dossiers"]
    for key in required:
        if key not in body:
            return False, f"missing required key: {key}"
    if body["operation"] != "propose":
        return False, "operation must be 'propose'"
    if not isinstance(body["evaluation_id"], str):
        return False, "evaluation_id must be a string"
    if not isinstance(body["dossiers"], list) or not body["dossiers"]:
        return False, "dossiers must be a non-empty list"
    return True, None


def validate_commit_request(body):
    if not isinstance(body, dict):
        return False, "body must be a JSON object"
    required = ["operation", "receipts"]
    for key in required:
        if key not in body:
            return False, f"missing required key: {key}"
    if body["operation"] != "commit":
        return False, "operation must be 'commit'"
    if not isinstance(body["receipts"], list) or not body["receipts"]:
        return False, "receipts must be a non-empty list"
    return True, None
