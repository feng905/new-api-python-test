"""
测试基础设施 - 通用工具函数、API 客户端、结果收集器
"""
import json
import time
import sqlite3
import requests
from dataclasses import dataclass, field
from typing import Optional
from config.settings import (
    BASE_URL, DB_PATH, ADMIN_ACCESS_TOKEN, ADMIN_USER_ID,
    VALID_TOKEN, INVALID_TOKEN, TEST_MODEL_OPENAI, TEST_MODEL_CLAUDE,
    REPORT_DIR
)


@dataclass
class TestCaseResult:
    name: str
    category: str
    passed: bool
    score: float = 0.0
    max_score: float = 1.0
    detail: str = ""
    duration_ms: float = 0.0
    request_id: str = ""


@dataclass
class TestSuiteResult:
    category: str
    results: list = field(default_factory=list)

    @property
    def total_score(self):
        return sum(r.score for r in self.results)

    @property
    def max_score(self):
        return sum(r.max_score for r in self.results)

    @property
    def pass_count(self):
        return sum(1 for r in self.results if r.passed)

    @property
    def total_count(self):
        return len(self.results)

    @property
    def pass_rate(self):
        return self.pass_count / self.total_count if self.total_count else 0


class APIClient:
    def __init__(self, base_url=BASE_URL, token=VALID_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        })

    def set_token(self, token):
        self.token = token
        self.session.headers["Authorization"] = "Bearer {}".format(token)

    def chat_completions(self, model=TEST_MODEL_OPENAI, messages=None,
                         stream=False, temperature=1.0, top_p=1.0,
                         max_tokens=None, **kwargs):
        payload = {
            "model": model,
            "messages": messages or [{"role": "user", "content": "hello"}],
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        url = "{}/v1/chat/completions".format(self.base_url)
        if stream:
            resp = self.session.post(url, json=payload, stream=True)
            return resp
        return self.session.post(url, json=payload)

    def responses_api(self, model=TEST_MODEL_OPENAI, input_data=None,
                       stream=False, **kwargs):
        payload = {
            "model": model,
            "input": input_data or [
                {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": "hello"}]}],
            "stream": stream,
        }
        payload.update(kwargs)
        url = "{}/v1/responses".format(self.base_url)
        if stream:
            return self.session.post(url, json=payload, stream=True)
        return self.session.post(url, json=payload)

    def messages_api(self, model=TEST_MODEL_CLAUDE, messages=None,
                      stream=False, max_tokens=1024, **kwargs):
        payload = {
            "model": model,
            "messages": messages or [{"role": "user", "content": "hello"}],
            "max_tokens": max_tokens,
            "stream": stream,
        }
        payload.update(kwargs)
        url = "{}/v1/messages".format(self.base_url)
        if stream:
            return self.session.post(url, json=payload, stream=True)
        return self.session.post(url, json=payload)

    def models_list(self):
        return self.session.get("{}/v1/models".format(self.base_url))

    def admin_request(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": "Bearer {}".format(ADMIN_ACCESS_TOKEN),
            "X-Api-User": ADMIN_USER_ID,
        })
        return self.session.request(
            method, "{}{}".format(self.base_url, path),
            headers=headers, **kwargs)


class DBHelper:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_logs(self, limit=100, request_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if request_id:
                cur.execute(
                    "SELECT * FROM logs WHERE request_id=? ORDER BY id DESC LIMIT ?",
                    (request_id, limit))
            else:
                cur.execute(
                    "SELECT * FROM logs ORDER BY id DESC LIMIT ?",
                    (limit,))
            return [dict(r) for r in cur.fetchall()]


def parse_stream_chunks(response):
    """解析 SSE 流式响应，返回所有 chunk 列表"""
    chunks = []
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            chunks.append(chunk)
        except json.JSONDecodeError:
            continue
    return chunks


def collect_stream_content(chunks):
    """从流式 chunks 中收集完整文本内容"""
    content = ""
    for chunk in chunks:
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content += delta.get("content", "")
    return content
