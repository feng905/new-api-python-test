#!/usr/bin/env python3
"""new-api 自动化测试主运行器 - 纯测试逻辑，无 HTML 模板"""
import sys
import os
import json
import time
import select
import sqlite3
import statistics
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# 加载 .env 配置（从项目根目录）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ============================================================
# 配置（从环境变量 / .env 文件读取）
# ============================================================
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
DB_PATH = os.getenv("DB_PATH", "../new-api-yingcai/one-api.db")
VALID_TOKEN = os.getenv("VALID_TOKEN", "")
INVALID_TOKEN = os.getenv("INVALID_TOKEN", "sk-invalid-token-00000000000000000000000000000000")
TEST_MODEL_OPENAI = os.getenv("TEST_MODEL_OPENAI", "gpt-3.5-turbo")


REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

# 超时配置（秒）：普通请求 / 大请求
TIMEOUT_NORMAL = 30
TIMEOUT_LARGE = 60

results_all = []


def add_result(name, category, passed, score, max_score, detail,
               duration_ms=0, request_id=""):
    results_all.append({
        "name": name,
        "category": category,
        "passed": passed,
        "score": score,
        "max_score": max_score,
        "detail": detail,
        "duration_ms": duration_ms,
        "request_id": request_id,
    })


def make_client(token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token),
    })
    return s


def chat(s, messages=None, stream=False, **kwargs):
    payload = {
        "model": TEST_MODEL_OPENAI,
        "messages": messages or [{"role": "user", "content": "hello"}],
        "stream": stream,
    }
    payload.update(kwargs)
    return s.post("{}/v1/chat/completions".format(BASE_URL),
                  json=payload, stream=stream, timeout=TIMEOUT_NORMAL)


def parse_sse(r):
    chunks = []
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data = line[6:]
        if data.strip() == "[DONE]":
            break
        try:
            chunks.append(json.loads(data))
        except Exception:
            continue
    return chunks


# ============================================================
# 测试1：连通性与鉴权
# ============================================================
def test_auth():
    print("\n[1/5] 连通性与鉴权测试")
    s = make_client(VALID_TOKEN)

    # 1.1 有效 token
    t0 = time.time()
    r = chat(s)
    ms = (time.time() - t0) * 1000
    ok = r.status_code == 200
    add_result("有效Token返回200", "连通性与鉴权测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "status={}".format(r.status_code), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 有效Token: {}".format("PASS" if ok else "FAIL",
          r.status_code))

    # 1.2 无效 token
    s2 = make_client(INVALID_TOKEN)
    t0 = time.time()
    r = chat(s2)
    ms = (time.time() - t0) * 1000
    ok = r.status_code == 401
    add_result("无效Token返回401", "连通性与鉴权测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "status={}".format(r.status_code), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 无效Token: {}".format("PASS" if ok else "FAIL",
          r.status_code))

    # 1.3 无 token
    s3 = make_client("")
    s3.headers.pop("Authorization", None)
    t0 = time.time()
    r = chat(s3)
    ms = (time.time() - t0) * 1000
    ok = r.status_code in (401, 403)
    add_result("无Token返回401或403", "连通性与鉴权测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "status={}".format(r.status_code), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 无Token: {}".format("PASS" if ok else "FAIL",
          r.status_code))

    # 1.4 100次连续请求
    s = make_client(VALID_TOKEN)
    latencies = []
    suc = 0
    codes = {}
    for i in range(100):
        t0 = time.time()
        try:
            r = chat(s)
            el = (time.time() - t0) * 1000
            latencies.append(el)
            c = r.status_code
            codes[c] = codes.get(c, 0) + 1
            if c == 200:
                suc += 1
        except requests.exceptions.Timeout:
            latencies.append(-1)
            codes["timeout"] = codes.get("timeout", 0) + 1
        except Exception:
            latencies.append(-1)
            codes["error"] = codes.get("error", 0) + 1

    rate = suc / 100.0
    valid = [l for l in latencies if l >= 0]
    avg = statistics.mean(valid) if valid else -1
    p95 = sorted(valid)[int(len(valid) * 0.95)] if len(valid) >= 20 else -1
    score = min(rate, 1.0)
    add_result("100次连续请求稳定性", "连通性与鉴权测试",
                rate >= 0.95, score, 1.0,
                "成功率={:.1%} 平均={:.0f}ms P95={:.0f}ms codes={}".format(
                    rate, avg, p95, codes),
                sum(valid),
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 100次连续: 成功率={:.1%}".format(
        "PASS" if rate >= 0.95 else "FAIL", rate))


# ============================================================
# 测试2：协议兼容性
# ============================================================
def test_protocol():
    print("\n[2/5] 协议兼容性测试")
    s = make_client(VALID_TOKEN)

    # 2.1 基础 chat
    t0 = time.time()
    r = chat(s, messages=[{"role": "user", "content": "say hi"}])
    ms = (time.time() - t0) * 1000
    ok = False
    detail = ""
    if r.status_code == 200:
        try:
            d = r.json()
            content = d["choices"][0]["message"]["content"]
            ok = bool(content and len(content) > 0)
            detail = "content_len={}".format(len(content))
        except Exception as e:
            detail = "parse error: {}".format(e)
    else:
        detail = "status={}".format(r.status_code)
    add_result("基础chat返回choices[0].message.content",
                "协议兼容性测试", ok, 1.0 if ok else 0.0, 1.0,
                detail, ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 基础chat: {}".format("PASS" if ok else "FAIL", detail))

    # 2.2 参数传递
    t0 = time.time()
    r = chat(s, messages=[{"role": "user", "content": "hi"}],
             temperature=0.5, top_p=0.8, max_tokens=50)
    ms = (time.time() - t0) * 1000
    ok = r.status_code == 200
    add_result("接受temperature+top_p+max_tokens",
                "协议兼容性测试", ok, 1.0 if ok else 0.0, 1.0,
                "status={}".format(r.status_code), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 参数传递: status={}".format(
        "PASS" if ok else "FAIL", r.status_code))

    # 2.3 流式响应
    t0 = time.time()
    r = chat(s, messages=[{"role": "user", "content": "stream test"}],
             stream=True)
    ms = (time.time() - t0) * 1000
    chunks = parse_sse(r)
    ok = len(chunks) >= 5
    add_result("流式响应stream=true返回>=5块",
                "协议兼容性测试", ok, 1.0 if ok else 0.0, 1.0,
                "chunks={}".format(len(chunks)), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 流式响应: chunks={}".format(
        "PASS" if ok else "FAIL", len(chunks)))

    # 2.4 system role
    t0 = time.time()
    r = chat(s, messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hi"},
    ])
    ms = (time.time() - t0) * 1000
    ok = r.status_code == 200
    add_result("支持system role消息",
                "协议兼容性测试", ok, 1.0 if ok else 0.0, 1.0,
                "status={}".format(r.status_code), ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} system role: status={}".format(
        "PASS" if ok else "FAIL", r.status_code))

    # 2.5 参数真实生效
    t0 = time.time()
    r = chat(s, messages=[{"role": "user", "content": "Tell me a story"}],
             max_tokens=5)
    ms = (time.time() - t0) * 1000
    ok = False
    detail = ""
    if r.status_code == 200:
        try:
            d = r.json()
            usage = d.get("usage", {})
            tokens = usage.get("completion_tokens", 999)
            ok = tokens <= 10
            detail = "completion_tokens={}".format(tokens)
        except Exception as e:
            detail = "parse error: {}".format(e)
    else:
        detail = "status={}".format(r.status_code)
    add_result("参数真实生效验证max_tokens=5",
                "协议兼容性测试", ok, 1.0 if ok else 0.0, 1.0,
                detail, ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 参数生效: {}".format("PASS" if ok else "FAIL", detail))

    # 2.6 流式输出完整性
    t0 = time.time()
    r = chat(s, messages=[{"role": "user", "content": "hi"}],
             stream=True)
    ms = (time.time() - t0) * 1000
    chunks = parse_sse(r)
    content = ""
    has_stop = False
    for c in chunks:
        for choice in c.get("choices", []):
            content += choice.get("delta", {}).get("content", "")
            if choice.get("finish_reason") == "stop":
                has_stop = True
    ok = len(content) > 0 and has_stop
    add_result("流式输出完整性", "协议兼容性测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "content_len={} finish_stop={}".format(len(content), has_stop),
                ms,
                r.headers.get("X-Api-Request-Id", ""))
    print("  {} 流式完整: ok={} len={}".format(
        "PASS" if ok else "FAIL", ok, len(content)))


# ============================================================
# 测试3：限流
# ============================================================
def test_stability():
    print("\n[5/5] 限流测试")
    s = make_client(VALID_TOKEN)

    # 3.1 触发限流
    status_codes = []
    resp_429_list = []

    def burst():
        try:
            return chat(s)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(burst) for _ in range(50)]
        for f in as_completed(futures, timeout=60):
            try:
                r = f.result()
            except Exception:
                continue
            if r is None:
                continue
            sc = r.status_code
            status_codes.append(sc)
            if sc == 429:
                resp_429_list.append(r)

    resp_429 = resp_429_list[0] if resp_429_list else None

    codes_count = {}
    for c in status_codes:
        codes_count[c] = codes_count.get(c, 0) + 1
    ok = resp_429 is not None
    if ok:
        ra = resp_429.headers.get("Retry-After", "(missing)")
        detail = "429触发成功, Retry-After={} 状态码分布={}".format(ra, codes_count)
    else:
        detail = "未触发429 状态码分布={}".format(codes_count)
    add_result("限流响应429状态码", "限流测试",
                ok, 1.0 if ok else 0.0, 1.0, detail, 0,
                resp_429.headers.get("X-Api-Request-Id", "") if resp_429 else "")
    print("  {} 限流429: {}".format("PASS" if ok else "FAIL", detail))

    # 3.2 Retry-After 头
    ok2 = False
    if resp_429 is not None:
        ra = resp_429.headers.get("Retry-After")
        ok2 = ra is not None and ra != ""
        detail2 = "Retry-After={}".format(ra) if ok2 else "缺失Retry-After头"
    else:
        detail2 = "未触发429，无法检查"
    add_result("429响应带Retry-After头", "限流测试",
                ok2, 1.0 if ok2 else 0.0, 1.0, detail2, 0,
                resp_429.headers.get("X-Api-Request-Id", "") if resp_429 is not None else "")
    print("  {} Retry-After: {}".format(
        "PASS" if ok2 else "FAIL", detail2))

    # 3.3 独立限流（简化）
    # add_result("不同接口独立限流", "限流测试",
    #             ok, 1.0 if ok else 0.0, 1.0,
    #             "chat限流={}".format(ok), 0,
    #             resp_429.headers.get("X-Api-Request-Id", "") if resp_429 is not None else "")
    # print("  {} 独立限流: chat={}".format("PASS" if ok else "FAIL", ok))

    # 3.4 稳定调用20次
    # suc = 0
    # errs = []
    # last_r = None
    # for i in range(20):
    #     try:
    #         r = chat(s)
    #         last_r = r
    #         if r.status_code == 200:
    #             suc += 1
    #         else:
    #             errs.append(str(r.status_code))
    #     except requests.exceptions.Timeout:
    #         errs.append("timeout")
    #     except Exception as e:
    #         errs.append(str(e)[:30])
    #     time.sleep(0.05)
    # rate = suc / 20.0
    # score = min(rate, 1.0)
    # add_result("接口长期稳定调用20次", "限流测试",
    #             rate >= 0.95, score, 1.0,
    #             "成功率={:.1%} errors={}".format(rate, errs[:3]), 0,
    #             last_r.headers.get("X-Api-Request-Id", "") if last_r else "")
    # print("  {} 稳定调用: 成功率={:.1%}".format(
    #     "PASS" if rate >= 0.95 else "FAIL", rate))


# ============================================================
# 测试4：异常容错
# ============================================================
def test_error():
    print("\n[3/5] 异常容错测试")
    s = make_client(VALID_TOKEN)

    cases = [
            ("超大输入1M字符返回400/413",
            lambda: s.post("{}/v1/chat/completions".format(BASE_URL),
                        json={"model": "gpt-3.5-turbo",
                                "messages": [{"role": "user",
                                            "content": "a" * 1000000}]},
                        timeout=TIMEOUT_LARGE*10),
            lambda r: r.status_code in (400, 413, 422, 502)),
    ]

    cases = [
        ("不存在模型返回400/404",
         lambda: s.post("{}/v1/chat/completions".format(BASE_URL),
                      json={"model": "nonexistent-model-xyz",
                            "messages": [{"role": "user", "content": "hi"}]},
                      timeout=TIMEOUT_NORMAL),
         lambda r: r.status_code in (400, 404, 422)),
        ("messages为空返回400",
         lambda: s.post("{}/v1/chat/completions".format(BASE_URL),
                      json={"model": "gpt-3.5-turbo", "messages": []},
                      timeout=TIMEOUT_NORMAL),
         lambda r: r.status_code in (400, 422)),
        ("非法JSON返回400",
         lambda: s.post("{}/v1/chat/completions".format(BASE_URL),
                      data="{invalid json}",
                      headers={"Content-Type": "application/json"},
                      timeout=TIMEOUT_NORMAL),
         lambda r: r.status_code in (400, 422)),
        ("超大输入1M字符返回400/413",
         lambda: s.post("{}/v1/chat/completions".format(BASE_URL),
                      json={"model": "gpt-3.5-turbo",
                            "messages": [{"role": "user",
                                          "content": "a" * 1000000}]},
                      timeout=TIMEOUT_LARGE*10),
         lambda r: r.status_code in (400, 413, 422, 502)),
        ("无Authorization返回401/403",
         lambda: requests.post(
             "{}/v1/chat/completions".format(BASE_URL),
             json={"model": "gpt-3.5-turbo",
                   "messages": [{"role": "user", "content": "hi"}]},
             timeout=TIMEOUT_NORMAL),
         lambda r: r.status_code in (401, 403)),
    ]

    for name, req_fn, check_fn in cases:
        t0 = time.time()
        rid = ""
        try:
            r = req_fn()
            ms = (time.time() - t0) * 1000
            ok = check_fn(r)
            rid = r.headers.get("X-Api-Request-Id", "")
            retry_after = r.headers.get("Retry-After", "")
            detail = "status={} headers=Retry-After:{}".format(
                r.status_code, retry_after if retry_after else "(无)")
            # 如果收到429，额外输出响应体前200字符帮助排查
            if r.status_code == 429:
                try:
                    body = r.text[:200]
                except Exception:
                    body = "(无法读取)"
                detail += " body={}".format(body)
        except requests.exceptions.Timeout:
            ms = (time.time() - t0) * 1000
            ok = False
            detail = "请求超时"
        except Exception as e:
            ms = (time.time() - t0) * 1000
            ok = False
            detail = "exception: {}".format(str(e)[:100])
        add_result(name, "异常容错测试",
                    ok, 1.0 if ok else 0.0, 1.0, detail, ms, rid)
        print("  {} {}: {}".format(
            "PASS" if ok else "FAIL", name, detail))


# ============================================================
# 测试5：request_id 透传
# ============================================================
def test_request_id():
    print("\n[4/5] request_id 透传测试")
    s = make_client(VALID_TOKEN)

    # 5.1 响应头包含 X-Api-Request-Id
    r = chat(s)
    rid = r.headers.get("X-Api-Request-Id", "")
    ok = bool(rid and len(rid) > 5)
    add_result("响应头包含X-Api-Request-Id", "request_id 透传测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "X-Api-Request-Id={}".format(rid[:30] if rid else "(空)"),
                0, rid)
    print("  {} 响应头request_id: {}".format(
        "PASS" if ok else "FAIL", rid[:20] if rid else "(空)"))

    # 5.2 唯一性
    rids = set()
    last_rid = ""
    for i in range(20):
        resp = chat(s)
        rid_i = resp.headers.get("X-Api-Request-Id", "")
        if rid_i:
            rids.add(rid_i)
        last_rid = rid_i
    ok = len(rids) >= 15
    add_result("request_id唯一性20次>=15", "request_id 透传测试",
                ok, 1.0 if ok else 0.0, 1.0,
                "唯一数={}/20".format(len(rids)), 0, last_rid)
    print("  {} request_id唯一性: {}/20".format(
        "PASS" if ok else "FAIL", len(rids)))

    # 5.3 数据库日志覆盖率
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM logs WHERE id > "
                "(SELECT MAX(id)-100 FROM logs)")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM logs WHERE id > "
                "(SELECT MAX(id)-100 FROM logs) "
                "AND request_id IS NOT NULL AND request_id != ''")
            with_rid = cur.fetchone()[0]
            coverage = with_rid / total if total > 0 else 0
            ok = coverage >= 0.99
            add_result("日志request_id覆盖率>=99%", "request_id 透传测试",
                        ok, min(coverage, 1.0), 1.0,
                        "覆盖率={:.1%} ({}/{})".format(
                            coverage, with_rid, total))
    except Exception as e:
        add_result("日志request_id覆盖率>=99%", "request_id 透传测试",
                    False, 0.0, 1.0,
                    "DB查询异常: {}".format(str(e)[:100]))
    print("  {} 日志覆盖率".format("PASS" if ok else "FAIL"))

    # 5.4 响应体透传
    # r = chat(s)
    # rid_header = r.headers.get("X-Api-Request-Id", "")
    # try:
    #     d = r.json()
    #     rid_body = d.get("request_id", "")
    # except Exception:
    #     rid_body = ""
    # ok = bool(rid_body)
    # add_result("request_id在响应体中透传", "request_id 透传测试",
    #             ok, 1.0 if ok else 0.5, 1.0,
    #             "header_rid={} body_rid={}".format(
    #                 rid_header[:20] if rid_header else "",
    #                 rid_body[:20] if rid_body else ""),
    #             0, rid_header)
    # print("  {} 响应体透传: body_rid={}".format(
    #     "PASS" if ok else "WARN", rid_body[:20] if rid_body else "(空)"))


# ============================================================
# 保存结果 + 生成报告
# ============================================================
def save_results():
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORT_DIR, "report_{}.json".format(ts))
    report = {
        "generated_at": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "results": results_all,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\nJSON 结果已保存：{}".format(json_path))
    return json_path


def print_summary():
    total_pass = sum(1 for r in results_all if r["passed"])
    total_cnt = len(results_all)
    total_score = sum(r["score"] for r in results_all)
    total_max = sum(r["max_score"] for r in results_all)

    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)
    print("  总通过率：{}/{} ({:.1%})".format(
        total_pass, total_cnt,
        total_pass / total_cnt if total_cnt else 0))
    print("  总得分：  {:.1f} / {:.1f}".format(total_score, total_max))
    print("=" * 60)
    return total_pass, total_cnt, total_score, total_max


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  new-api 自动化测试")
    print("  被测系统：{}".format(BASE_URL))
    print("  开始时间：{}".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 60)

    t0 = time.time()
    test_auth()
    test_protocol()
    test_error()
    test_request_id()
    elapsed = (time.time() - t0) * 1000

    # 限流测试放最后，等用户确认或30秒超时后自动执行
    print("\n" + "-" * 60)
    print("  即将执行限流测试（会触发大量并发请求，可能影响服务）")
    print("  按回车键立即执行，或等待 30 秒自动开始...")
    print("-" * 60)

    if sys.platform != "win32":
        # macOS / Linux: 用 select 实现超时
        rlist, _, _ = select.select([sys.stdin], [], [], 30)
        if rlist:
            sys.stdin.readline()
    else:
        # Windows: 简单 sleep
        time.sleep(30)

    test_stability()

    print_summary()
    json_path = save_results()

    print("\n原始结果（JSON）：{}".format(json_path))
    print("用 generate_report.py 生成 HTML 报告：")
    print("  python3 generate_report.py {}".format(json_path))
