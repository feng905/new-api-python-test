"""
测试1：连通性与鉴权测试
根据 Excel 第1行需求：
- 测试有效Token：HTTP 200
- 测试无效Token：HTTP 401
- 测试无Token请求：HTTP 403
- 持续发起100次测试，取平均值按比例得分
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import statistics
from tests.base import APIClient, TestCaseResult, TestSuiteResult
from config.settings import VALID_TOKEN, INVALID_TOKEN, TEST_MODEL_OPENAI


def run_auth_tests():
    suite = TestSuiteResult(category="连通性与鉴权测试")
    client = APIClient(token=VALID_TOKEN)

    # Test 1.1: 有效 Token
    client.set_token(VALID_TOKEN)
    start = time.time()
    resp = client.chat_completions()
    duration = (time.time() - start) * 1000

    passed = resp.status_code == 200
    suite.results.append(TestCaseResult(
        name="u6709u6548Tokenu8bf7u6c42u8fd4u56de200",
        category="u8fdeu901au6027u4e0eu9274u6743u6d4bu8bd5",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=u72b6u6001u7801: {}u671fu671b: 200".format(resp.status_code),
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # Test 1.2: 无效 Token
    client.set_token(INVALID_TOKEN)
    start = time.time()
    resp = client.chat_completions()
    duration = (time.time() - start) * 1000

    passed = resp.status_code == 401
    suite.results.append(TestCaseResult(
        name="u65e0u6548Tokenu8bf7u6c42u8fd442",
        category="u8fdeu901au6027u4e0eu9274u6743u6d4bu8bd5",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=u72b6u6001u7801: {}u671f: 401".format(resp.status_code),
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # Test 1.3: 无 Token 请求
    client_no_auth = APIClient(token="")
    client_no_auth.session.headers.pop("Authorization", None)
    start = time.time()
    resp = client_no_auth.chat_completions()
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (401, 403)
    suite.results.append(TestCaseResult(
        name="u65e0Tokenu8bf7u6c42u8fd441/443",
        category="u8fdeu901au6027u4e0eu9274u6743u6d4bu8bd5",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=u72b6u6001u7801: {}u671f: 401u6216437".format(resp.status_code),
        duration_ms=duration,
    ))

    # Test 1.4: 100次连续请求稳定性
    client.set_token(VALID_TOKEN)
    latencies = []
    success_count = 0
    status_codes = {}

    for i in range(100):
        start = time.time()
        try:
            resp = client.chat_completions()
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            code = resp.status_code
            status_codes[code] = status_codes.get(code, 0) + 1
            if code == 200:
                success_count += 1
        except Exception:
            latencies.append(-1)
            status_codes["error"] = status_codes.get("error", 0) + 1

    success_rate = success_count / 100.0
    valid_latencies = [l for l in latencies if l >= 0]
    avg_latency = statistics.mean(valid_latencies) if valid_latencies else -1
    p95_index = min(94, len(valid_latencies) - 1)
    p95_latency = sorted(valid_latencies)[p95_index] if valid_latencies else -1

    passed = success_rate >= 0.95
    score = min(success_rate, 1.0)
    suite.results.append(TestCaseResult(
        name="100u6b21u8fdeu7eedu8bf7u6c42u7a33u5b9au6027u2951u203495u0025",
        category="u8fdeu901au6027u4e0eu9274u6743u6d4bu8bd5",
        passed=passed,
        score=score,
        max_score=1.0,
        detail=u6210u529fu7387: {:.1%}, u5e73u5747u5ef6u8fdf: {:.1f}ms, P95: {:.1f}ms, u72b6u6001u7801u5206u5e03: {}".format(
            success_rate, avg_latency, p95_latency, status_codes),
        duration_ms=sum(valid_latencies),
    ))

    return suite


if __name__ == "__main__":
    result = run_auth_tests()
    for r in result.results:
        status = "u2705" if r.passed else "u274c"
        print("{} {}: {}".format(status, r.name, r.detail))
    print("\nu603bu5206: {:.1f}/{:.1f} u9014u8fc7u7387: {:.1%}".format(
        result.total_score, result.max_score, result.pass_rate))
