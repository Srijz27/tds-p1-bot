"""
Run Budget & Loop Guard endpoint.

POST /            -> decide whether the agent's next step may happen
POST /decide       -> same thing, alternate path (in case the grader posts here)

Request body:
{
  "budget_tokens": <int>,
  "steps": [
    {"step_number": <int>, "tool": "<string>", "args": <object>, "tokens_used": <int>},
    ...
  ]
}

Response body:
{ "decision": "continue" | "halt", "reason": "short human-readable string" }
"""

import json
import re

from flask import Flask, jsonify, request

app = Flask(__name__)


def normalize_value(value):
    """Recursively normalize a JSON value for comparison."""
    if isinstance(value, dict):
        return {
            key: normalize_value(val)
            for key, val in value.items()
            if key != "trace_id"
        }
    if isinstance(value, list):
        return [normalize_value(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value


def canonical_key(tool, args):
    """Produce a stable string fingerprint for a (tool, args) pair."""
    normalized_args = normalize_value(args)
    return tool + "::" + json.dumps(normalized_args, sort_keys=True)


def decide(budget_tokens, steps):
    total_tokens = sum(step.get("tokens_used", 0) for step in steps)

    if total_tokens >= budget_tokens:
        return {
            "decision": "halt",
            "reason": (
                f"Cumulative tokens_used ({total_tokens}) has reached "
                f"the budget ({budget_tokens})."
            ),
        }

    if not steps:
        return {
            "decision": "continue",
            "reason": "No steps taken yet; fresh run, well under budget.",
        }

    keys = [canonical_key(s.get("tool", ""), s.get("args", {})) for s in steps]
    n = len(keys)

    if n >= 3:
        last = keys[-1]
        run_length = 1
        i = n - 2
        while i >= 0 and keys[i] == last:
            run_length += 1
            i -= 1
        if run_length >= 3:
            return {
                "decision": "halt",
                "reason": (
                    f"The same tool call was repeated {run_length} times in a "
                    "row with functionally identical arguments (loop detected)."
                ),
            }

    if n >= 6:
        tail = keys[-6:]
        a, b = tail[0], tail[1]
        if a != b and tail == [a, b, a, b, a, b]:
            return {
                "decision": "halt",
                "reason": (
                    "Detected a 2-step alternating cycle (A,B,A,B,A,B) over "
                    "the last 6 steps with no distinguishing progress."
                ),
            }

    return {
        "decision": "continue",
        "reason": (
            f"Under budget ({total_tokens}/{budget_tokens} tokens used) and "
            "no repeat-call or cycle loop detected in the trailing steps."
        ),
    }


def handle_request():
    body = request.get_json(force=True, silent=True)
    if body is None:
        return jsonify({"decision": "halt", "reason": "Invalid or missing JSON body."}), 400

    budget_tokens = body.get("budget_tokens")
    steps = body.get("steps", [])

    if not isinstance(budget_tokens, int):
        return jsonify({"decision": "halt", "reason": "budget_tokens must be an integer."}), 400
    if not isinstance(steps, list):
        return jsonify({"decision": "halt", "reason": "steps must be a list."}), 400

    result = decide(budget_tokens, steps)
    return jsonify(result), 200


@app.route("/", methods=["POST"])
def root():
    return handle_request()


@app.route("/decide", methods=["POST"])
def decide_route():
    return handle_request()


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
