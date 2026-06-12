#!/usr/bin/env python3
"""
本地模拟渠道服务 - OpenAI API 兼容接口
支持：chat completions (流式/非流式)、responses、messages 协议
运行: python3 mock_server.py [port]
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import uuid
import threading

MOCK_RESPONSES = {
    "gpt-3.5-turbo": "Hello! I'm a mock GPT-3.5-turbo response. How can I help you today?",
    "gpt-5.2": "I'm a mock GPT-5.2 model. This is a simulated response for testing purposes.",
    "claude-opus-4-6": "Hello! I'm a mock Claude Opus 4.6 response. I can assist you with various tasks.",
    "gemini-3-pro-image-preview": "I'm a mock Gemini 3 Pro model response.",
    "360gpt-turbo": "I'm a mock 360GPT Turbo response.",
    "360gpt-pro": "I'm a mock 360GPT Pro response.",
}

rate_limiter = {}
rate_lock = threading.Lock()

request_log = []
request_log_lock = threading.Lock()


def log(msg):
    print(f"[Mock] {msg}", flush=True)


def check_rate(token, max_rps=10):
    with rate_lock:
        now = time.time()
        if token not in rate_limiter:
            rate_limiter[token] = []
        window_start = now - 60
        rate_limiter[token] = [t for t in rate_limiter[token] if t > window_start]
        if len(rate_limiter[token]) >= max_rps * 60:
            return False
        rate_limiter[token].append(now)
        return True


def make_chat_response(model, content, request_id, created, stream=False):
    if stream:
        return None  # handled separately
    return {
        "id": "chatcmpl-" + request_id[:24],
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": len(content.split()),
            "total_tokens": 10 + len(content.split())
        },
        "request_id": request_id
    }


def make_stream_chunks(model, content, request_id, created):
    words = content.split()
    chunks = []
    for i, w in enumerate(words):
        delta = {"content": w + " "}
        if i == 0:
            delta["role"] = "assistant"
        chunks.append({
            "id": "chatcmpl-" + request_id[:24],
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
        })
    chunks.append({
        "id": "chatcmpl-" + request_id[:24],
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
    })
    return chunks


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def _headers_dict(self):
        return {k: v for k, v in self.headers.items()}

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send(self, code, obj, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-Id", str(uuid.uuid4()))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _stream(self, content_type, generator):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        rid = str(uuid.uuid4())
        self.send_header("X-Request-Id", rid)
        self.end_headers()
        for chunk in generator(rid):
            self.wfile.write(chunk)
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def do_GET(self):
        self._send(405, {"error": {"message": "GET not allowed", "type": "invalid_request_error"}})

    def do_POST(self):
        body_bytes = self._read_body()
        body_str = body_bytes.decode("utf-8", errors="replace")
        log(f"POST {self.path}  body_len={len(body_bytes)}")

        # Parse JSON body
        try:
            data = json.loads(body_str) if body_str.strip() else {}
        except json.JSONDecodeError as e:
            self._send(400, {"error": {"message": f"Invalid JSON: {e}", "type": "invalid_request_error"}})
            return

        # Route by path - flexible matching
        path_clean = self.path.split("?")[0]

        if "chat/completions" in path_clean:
            self._handle_chat(body_bytes, data)
        elif "responses" in path_clean:
            self._handle_responses(data)
        elif "messages" in path_clean:
            self._handle_messages(data)
        elif "images/generations" in path_clean:
            self._handle_images(data)
        else:
            log(f"Unknown path: {self.path}")
            self._send(404, {"error": {"message": f"Unknown endpoint: {path_clean}", "type": "invalid_request_error"}})

    def _get_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return auth

    def _handle_chat(self, body_bytes, data):
        token = self._get_token()
        if not check_rate(token):
            self._send(429, {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
                        {"Retry-After": "30"})
            return

        model = data.get("model", "gpt-3.5-turbo")
        stream = data.get("stream", False)
        messages = data.get("messages", [])
        if not messages:
            self._send(400, {"error": {"message": "messages required", "type": "invalid_request_error"}})
            return

        content = MOCK_RESPONSES.get(model, f"Mock response for {model}.")
        rid = str(uuid.uuid4())
        created = int(time.time())

        if stream:
            chunks = make_stream_chunks(model, content, rid, created)
            def gen(rid):
                for c in chunks:
                    yield f"data: {json.dumps(c, ensure_ascii=False)}\n\n".encode("utf-8")
            self._stream("text/event-stream", gen)
        else:
            resp = make_chat_response(model, content, rid, created)
            self._send(200, resp)

    def _handle_responses(self, data):
        token = self._get_token()
        if not check_rate(token):
            self._send(429, {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
                        {"Retry-After": "30"})
            return
        model = data.get("model", "gpt-3.5-turbo")
        content = MOCK_RESPONSES.get(model, "Mock response.")
        rid = "resp-" + str(uuid.uuid4())
        self._send(200, {
            "id": rid,
            "object": "response",
            "status": "completed",
            "model": model,
            "output": [{
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}]
            }],
            "usage": {"input_tokens": 10, "output_tokens": len(content.split()), "total_tokens": 10 + len(content.split())}
        })

    def _handle_messages(self, data):
        token = self._get_token()
        if not check_rate(token):
            self._send(429, {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
                        {"Retry-After": "30"})
            return
        model = data.get("model", "claude-opus-4-6")
        content = MOCK_RESPONSES.get(model, "Mock Claude response.")
        self._send(200, {
            "id": "msg-" + str(uuid.uuid4()),
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": content}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": len(content.split())}
        })

    def _handle_images(self, data):
        self._send(200, {
            "created": int(time.time()),
            "data": [{"url": "https://example.com/mock-image.png"}]
        })


def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8881
    server = HTTPServer(("127.0.0.1", port), Handler)
    log(f"Listening on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
