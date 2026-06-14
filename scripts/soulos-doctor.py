#!/usr/bin/env python3
"""Preflight checks for SoulOS kernel + inference plug-in."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def fetch_json(url: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict | str]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def main() -> int:
    parser = argparse.ArgumentParser(description="SoulOS stack preflight")
    parser.add_argument("--kernel", default="http://localhost:8000")
    parser.add_argument("--inference", default="http://localhost:11434")
    parser.add_argument("--embedding-dimension", type=int, default=768)
    parser.add_argument("--bot-id", default="", help="Optional bot_id for hybrid/prepare smoke")
    args = parser.parse_args()

    errors: list[str] = []
    kernel = args.kernel.rstrip("/")

    print(f"Checking kernel {kernel} ...")
    status, body = fetch_json(f"{kernel}/health")
    if status != 200:
        errors.append(f"kernel health failed ({status}): {body}")
    else:
        print("  kernel health: ok")

    status, body = fetch_json(f"{kernel}/ready")
    if status not in (200, 503):
        errors.append(f"kernel ready failed ({status}): {body}")
    else:
        print(f"  kernel ready: {body.get('status', body) if isinstance(body, dict) else body}")

    if args.bot_id:
        print(f"Checking hybrid/prepare for bot {args.bot_id} ...")
        status, body = fetch_json(
            f"{kernel}/hybrid/prepare",
            method="POST",
            payload={
                "bot_id": args.bot_id,
                "query": "soulos doctor smoke test",
                "top_k": 1,
            },
        )
        if status != 200:
            errors.append(f"hybrid/prepare failed ({status}): {body}")
        elif isinstance(body, dict) and "system_prompt" not in body:
            errors.append("hybrid/prepare missing system_prompt")
        else:
            print("  hybrid/prepare: ok")

    print(f"Checking inference {args.inference} ...")
    status, body = fetch_json(args.inference.rstrip("/"))
    if status != 200:
        errors.append(f"inference health failed ({status}): {body}")
    else:
        print("  inference: ok")

    embed_url = f"{args.inference.rstrip('/')}/api/embeddings"
    status, body = fetch_json(
        embed_url,
        method="POST",
        payload={"model": "doctor-check", "prompt": "soulos doctor"},
    )
    if status != 200:
        errors.append(f"embeddings failed ({status}): {body}")
        errors.append("hint: set INFERENCE_API_URL to Ollama or inference bridge, not OpenAI /v1")
    else:
        dim = len(body.get("embedding", []))
        if dim != args.embedding_dimension:
            errors.append(
                f"embedding dimension mismatch: got {dim}, expected {args.embedding_dimension}"
            )
            errors.append("hint: align EMBEDDING_DIMENSION on kernel and bridge/embed model")
        else:
            print(f"  embeddings: ok ({dim} dims)")

    if errors:
        print("\nSoulOS doctor: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nSoulOS doctor: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
