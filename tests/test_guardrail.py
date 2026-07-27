import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main as main_module

client = TestClient(main_module.app)


def test_blocks_direct_read_of_protected_npmrc():
    response = client.post(
        "/guardrail",
        json={"tool": "bash", "command": "cat /home/agent/.npmrc"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"
    assert payload["reason"]


def test_blocks_tilde_expansion_of_protected_npmrc():
    response = client.post(
        "/guardrail",
        json={"tool": "bash", "command": "cat ~/.npmrc"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"


def test_allows_workspace_listing():
    response = client.post(
        "/guardrail",
        json={"tool": "bash", "command": "ls -la /home/agent/workspace"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"


def test_allows_write_inside_build():
    response = client.post(
        "/guardrail",
        json={
            "tool": "write_file",
            "path": "/home/agent/workspace/build/app.txt",
            "content": "ok",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"


def test_blocks_write_outside_build_with_traversal():
    response = client.post(
        "/guardrail",
        json={
            "tool": "write_file",
            "path": "/home/agent/workspace/../outside.txt",
            "content": "bad",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"


def test_blocks_disallowed_http_host():
    response = client.post(
        "/guardrail",
        json={"tool": "http_request", "method": "GET", "url": "https://example.com"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "block"


def test_allows_allowed_http_host():
    response = client.post(
        "/guardrail",
        json={"tool": "http_request", "method": "GET", "url": "https://registry.npmjs.org"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "allow"
