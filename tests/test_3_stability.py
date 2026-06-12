"""
测试3：稳定性与限流测试
根据 Excel 第4行需求：
- 观察限流响应：429状态码
- 限流策略测试：快速连续请求直到被限流
- 检查限流响应头：Retry-After
- 测试不同接口的独立限流
- 429响应需带Retry-After头
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tests.base import APIClient, TestCaseResult, TestSuiteResult, VALID_TOKEN


def run_stability_tests():
    suite = TestSuiteResult(category="稳定性与限流测试")
    client = APIClient(token=VALID_TOKEN)

    # === Test 3.1: 限流响应 429 状态码 ===
    rate_limit_hit = False
    rate_limit_response = None

    def burst_request():
        nonlocal rate_limit_hit, rate_limit_response
        try:
            r = client.chat_completions()
            if r.status_code == 429:
                rate_limit_hit = True
                rate_limit_response = r
                return True
        except Exception:
            pass
        return False

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(burst_request) for _ in range(50)]
        for future in as_completed(futures, timeout=30):
            if future.result():
                break

    passed = rate_limit_hit
    detail = ""
    if rate_limit_hit and rate_limit_response:
        retry_after = rate_limit_response.headers.get("Retry-After", "(缺失)")
        detail = "触发限流(429), Retry-After: {}".format(retry_after)
    else:
        detail = "未触发限流(429), 可能未配置限流策略或并发数不足"

    suite.results.append(TestCaseResult(
        name="限流响应429状态码",
        category="稳定性与限流测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
    ))

    # === Test 3.2: 429响应带Retry-After头 ===
    passed = False
    detail = ""
    if rate_limit_hit and rate_limit_response:
        retry_after = rate_limit_response.headers.get("Retry-After")
        passed = retry_after is not None and retry_after != ""
        detail = "Retry-After头: {}".format(retry_after) if passed else "未返回Retry-After头"

    suite.results.append(TestCaseResult(
        name="429响应带Retry-After头",
        category="稳定性与限流测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
    ))

    # === Test 3.3: 不同接口独立限流 ===
    chat_429 = False
    models_429 = False

    time.sleep(2)

    def test_chat_rate_limit():
        nonlocal chat_429
        with ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(lambda: client.chat_completions().status_code == 429) for _ in range(40)]
            for f in as_completed(futures, timeout=20):
                if f.result():
                    chat_429 = True
                    return

    def test_models_rate_limit():
        nonlocal models_429
        with ThreadPoolExecutor(max_workers=15) as ex:
            futures = [ex.submit(lambda: client.models_list().status_code == 429) for _ in range(40)]
            for f in as_completed(futures, timeout=20):
                if f.result():
                    models_429 = True
                    return

    t1 = threading.Thread(target=test_chat_rate_limit)
    t2 = threading.Thread(target=test_models_rate_limit)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    passed = chat_429 and models_429
    detail = "chat接口限流触发: {}, models接口限流触发: {}".format(chat_429, models_429)
    if not passed:
        detail += " (可能未配置限流或接口未独立限流)"

    suite.results.append(TestCaseResult(
        name="不同接口独立限流",
        category="稳定性与限流测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
    ))

    # === Test 3.4: 接口长期稳定调用 ===
    success_count = 0
    total = 20
    errors = []

    for i in range(total):
        try:
            resp = client.chat_completions()
            if resp.status_code == 200:
                success_count += 1
            else:
                errors.append("#{}: {}".format(i, resp.status_code))
        except Exception as e:
            errors.append("#{}: {}".format(i, str(e)[:50]))
        time.sleep(0.1)

    stability_rate = success_count / total
    passed = stability_rate >= 0.95
    score = min(stability_rate, 1.0)
    detail = "稳定调用成功率: {:.1%} ({}/{}), 错误: {}".format(
        stability_rate, success_count, total, errors[:3]
    )

    suite.results.append(TestCaseResult(
        name="接口长期稳定调用(20次)",
        category="稳定性与限流测试",
        passed=passed,
        score=score,
        max_score=1.0,
        detail=detail,
    ))

    return suite


if __name__ == "__main__":
    result = run_stability_tests()
    for r in result.results:
        status = "✅" if r.passed else "❌"
        print("{} {}: {}".format(status, r.name, r.detail))
    print("\n总分: {:.1f}/{:.1f} 通过率: {:.1%}".format(
        result.total_score, result.max_score, result.pass_rate))
