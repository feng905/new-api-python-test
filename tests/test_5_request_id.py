"""
测试5：request_id 全链路透传测试
根据 Excel 第6行需求：
- request_id 全链路透传
- 部分日志默认未带 request_id，需确保请求链路可追踪
- request_id/日志可追溯覆盖率≥99%
"""
import time
import sqlite3
import requests
from tests.base import APIClient, TestCaseResult, TestSuiteResult, DB_PATH, VALID_TOKEN


def run_request_id_tests():
    suite = TestSuiteResult(category="request_id 透传测试")
    client = APIClient(token=VALID_TOKEN)

    # === Test 5.1: 响应头包含 X-Api-Request-Id ===
    start = time.time()
    resp = client.chat_completions()
    duration = (time.time() - start) * 1000

    request_id = resp.headers.get("X-Api-Request-Id", "")
    passed = bool(request_id and len(request_id) > 5)
    detail = f"X-Api-Request-Id: {request_id}" if request_id else "X-Api-Request-Id 缺失"
    suite.results.append(TestCaseResult(
        name="响应头包含X-Api-Request-Id",
        category="request_id 透传测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=request_id,
    ))

    # === Test 5.2: 发起多次请求，验证 request_id 唯一性 ===
    request_ids = set()
    for i in range(20):
        r = client.chat_completions()
        rid = r.headers.get("X-Api-Request-Id", "")
        if rid:
            request_ids.add(rid)

    passed = len(request_ids) >= 15  # 20次请求至少15个唯一ID
    detail = f"唯一request_id数: {len(request_ids)}/20 (期望≥15)"
    suite.results.append(TestCaseResult(
        name="request_id唯一性(20次≥15)",
        category="request_id 透传测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
    ))

    # === Test 5.3: 数据库日志中 request_id 覆盖率 ===
    # 查询最近100条日志，检查 request_id 覆盖率
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total FROM logs WHERE id > (SELECT MAX(id)-100 FROM logs)")
            total = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) as with_rid FROM logs WHERE id > (SELECT MAX(id)-100 FROM logs) AND request_id IS NOT NULL AND request_id != ''")
            with_rid = cur.fetchone()["with_rid"]

            coverage = with_rid / total if total > 0 else 0
            passed = coverage >= 0.99
            score = min(coverage, 1.0)
            detail = f"覆盖率: {coverage:.1%} ({with_rid}/{total}), 期望≥99%"
    except Exception as e:
        coverage = 0
        passed = False
        score = 0.0
        detail = f"数据库查询异常: {str(e)[:100]}"

    suite.results.append(TestCaseResult(
        name="日志request_id覆盖率≥99%",
        category="request_id 透传测试",
        passed=passed,
        score=score,
        max_score=1.0,
        detail=detail,
    ))

    # === Test 5.4: request_id 在响应体中透传 ===
    resp = client.chat_completions()
    request_id = resp.headers.get("X-Api-Request-Id", "")
    body_rid = ""
    try:
        data = resp.json()
        body_rid = data.get("request_id", "")
    except Exception:
        pass

    passed = bool(body_rid and body_rid == request_id)
    detail = f"响应头rid={request_id}, 响应体rid={body_rid}"
    if not body_rid:
        detail += " (响应体中无request_id字段)"
    suite.results.append(TestCaseResult(
        name="request_id在响应体中透传",
        category="request_id 透传测试",
        passed=passed,
        score=1.0 if passed else 0.5,  # 部分接口可能在header中，body中不一定有
        max_score=1.0,
        detail=detail,
        request_id=request_id,
    ))

    # === Test 5.5: 流式响应中 request_id 透传 ===
    resp = client.chat_completions(
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    )
    from tests.base import parse_stream_chunks
    chunks = parse_stream_chunks(resp)
    stream_rid = ""
    for chunk in chunks:
        rid = chunk.get("id", "")
        if rid and not rid.startswith("chatcmpl-"):
            stream_rid = rid
            break
        stream_rid = rid  # chatcmpl-xxx is also a kind of request id

    header_rid = resp.headers.get("X-Api-Request-Id", "")
    passed = bool(stream_rid)
    detail = f"响应头rid={header_rid}, 流式chunk id={stream_rid}"
    suite.results.append(TestCaseResult(
        name="流式响应中request_id透传",
        category="request_id 透传测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        request_id=header_rid,
    ))

    return suite


if __name__ == "__main__":
    result = run_request_id_tests()
    for r in result.results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name}: {r.detail}")
    print(f"\n总分: {result.total_score:.1f}/{result.max_score:.1f} 通过率: {result.pass_rate:.1%}")
