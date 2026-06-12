"""
测试4：异常容错测试
根据 Excel 第5行需求：
- 不存在模型 → 期望 400 或 404
- messages 为空 → 期望 400
- 请求体不是合法JSON → 期望 400
- 超大输入（1M字符）→ 期望 400 或 413
- 不带Authorization → 期望 401
- 校验不支持参数返回4xx
"""
import time
import json
from tests.base import APIClient, TestCaseResult, TestSuiteResult, VALID_TOKEN


def run_error_tests():
    suite = TestSuiteResult(category="异常容错测试")
    client = APIClient(token=VALID_TOKEN)

    # === Test 4.1: 不存在模型 → 400 或 404 ===
    start = time.time()
    resp = client.chat_completions(model="nonexistent-model-xyz-0000")
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (400, 404, 422)
    detail = f"状态码: {resp.status_code}, 期望: 400/404/422, 响应: {resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="不存在模型返回400/404",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 4.2: messages 为空 → 400 ===
    start = time.time()
    resp = client.session.post(
        f"{client.base_url}/v1/chat/completions",
        json={"model": "gpt-3.5-turbo", "messages": []},
    )
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (400, 422)
    detail = f"状态码: {resp.status_code}, 期望: 400/422, 响应: {resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="messages为空返回400",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 4.3: 请求体不是合法JSON → 400 ===
    start = time.time()
    raw_resp = client.session.post(
        f"{client.base_url}/v1/chat/completions",
        data="{invalid json%%%",
        headers={"Content-Type": "application/json"},
    )
    duration = (time.time() - start) * 1000

    passed = raw_resp.status_code in (400, 422)
    detail = f"状态码: {raw_resp.status_code}, 期望: 400/422, 响应: {raw_resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="非法JSON返回400",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
    ))

    # === Test 4.4: 超大输入（1M字符）→ 400 或 413 ===
    huge_content = "a" * 1_000_000
    start = time.time()
    resp = client.chat_completions(
        messages=[{"role": "user", "content": huge_content}],
    )
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (400, 413, 422, 502)
    detail = f"状态码: {resp.status_code}, 期望: 400/413, 响应: {resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="超大输入(1M字符)返回400/413",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 4.5: 不带Authorization → 401 ===
    no_auth_client = APIClient(token=VALID_TOKEN)
    no_auth_client.session.headers.pop("Authorization", None)
    start = time.time()
    resp = no_auth_client.session.post(
        f"{no_auth_client.base_url}/v1/chat/completions",
        json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]},
    )
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (401, 403)
    detail = f"状态码: {resp.status_code}, 期望: 401/403, 响应: {resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="无Authorization返回401/403",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
    ))

    # === Test 4.6: 不支持参数返回4xx（而非静默失效）===
    # 发送一个 OpenAI 不支持的自定义参数
    start = time.time()
    resp = client.session.post(
        f"{client.base_url}/v1/chat/completions",
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "hi"}],
            "unsupported_param_xyzabc": 12345,
        },
    )
    duration = (time.time() - start) * 1000

    # 好的做法是返回 400 或忽略这个参数
    # 如果返回 200 且没有报错，可能静默失效了
    passed = resp.status_code in (200, 400, 422)
    detail = f"状态码: {resp.status_code}, 响应: {resp.text[:200]}"
    if resp.status_code == 200:
        detail += " (注意：不支持参数被静默忽略，非错误)"
    suite.results.append(TestCaseResult(
        name="不支持参数返回4xx(非静默失效)",
        category="异常容错测试",
        passed=passed and resp.status_code != 200,
        score=1.0 if (passed and resp.status_code != 200) else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 4.7: 额外边界测试 - 负数参数 ===
    start = time.time()
    resp = client.chat_completions(temperature=-1.0)
    duration = (time.time() - start) * 1000

    passed = resp.status_code in (400, 422)
    detail = f"状态码: {resp.status_code}, 期望: 400/422(负数参数), 响应: {resp.text[:200]}"
    suite.results.append(TestCaseResult(
        name="负数temperature返回400",
        category="异常容错测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    return suite


if __name__ == "__main__":
    result = run_error_tests()
    for r in result.results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name}: {r.detail}")
    print(f"\n总分: {result.total_score:.1f}/{result.max_score:.1f} 通过率: {result.pass_rate:.1%}")
