from flask import Flask, jsonify, request

from db import init_db
from schemas import validate_commit_request, validate_propose_request

app = Flask(__name__)
init_db()


@app.post('/mailroom')
def mailroom():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "body must be valid JSON"}), 400

    if body.get("operation") == "propose":
        ok, err = validate_propose_request(body)
        if not ok:
            return jsonify({"error": err}), 422
        return jsonify({
            "status": "ok",
            "operation": "propose",
            "proposal": {
                "type": "no_action",
                "evaluation_id": body["evaluation_id"],
                "reason": "stubbed proposal"
            }
        })

    if body.get("operation") == "commit":
        ok, err = validate_commit_request(body)
        if not ok:
            return jsonify({"error": err}), 422
        return jsonify({
            "status": "ok",
            "operation": "commit",
            "outcome": "no_action"
        })

    return jsonify({"error": "unsupported operation"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
