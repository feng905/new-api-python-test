"""
测试2：协议兼容性测试
根据 Excel 第2-3行需求：
- Claude模型支持messages协议
- OpenAI主流模型支持responses协议
- 基础chat返回choices[0].message.content
- 接受temperature+top_p+max_tokens参数
- 流式响应stream=true返回data:分块(收到5块)
- 支持system role消息
- 参数真实生效验证
- 流式输出完整性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import time
from tests.base import (
    APIClient, TestCaseResult, TestSuiteResult,
    parse_stream_chunks, collect_stream_content,
    VALID_TOKEN, TEST_MODEL_OPENAI, TEST_MODEL_CLAUDE
)


def run_protocol_tests():
    suite = TestSuiteResult(category="协议兼容性测试")
    client = APIClient(token=VALID_TOKEN)

    # === Test 2.1: 基础 chat 返回 choices[0].message.content ===
    start = time.time()
    resp = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[{"role": "user", "content": "Hello, say hi"}],
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    if resp.status_code == 200:
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            passed = bool(content and len(content) > 0)
            detail = f"返回内容长度: {len(content)}, 前50字: {content[:50]}"
        except (KeyError, IndexError) as e:
            detail = f"响应结构异常: {e}, 原始: {json.dumps(data, ensure_ascii=False)[:200]}"
    else:
        detail = f"状态码: {resp.status_code}, 响应: {resp.text[:200]}"

    suite.results.append(TestCaseResult(
        name="基础chat返回choices[0].message.content",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.2: 接受 temperature + top_p + max_tokens 参数 ===
    start = time.time()
    resp = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[{"role": "user", "content": "test params"}],
        temperature=0.5,
        top_p=0.8,
        max_tokens=50,
    )
    duration = (time.time() - start) * 1000

    passed = resp.status_code == 200
    detail = f"状态码: {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        detail += f", 响应正常, model={data.get('model', '')}"
    else:
        detail += f", 错误: {resp.text[:200]}"

    suite.results.append(TestCaseResult(
        name="接受temperature+top_p+max_tokens参数",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.3: 流式响应 stream=true 返回 data: 分块（收到5块） ===
    start = time.time()
    resp = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[{"role": "user", "content": "stream test"}],
        stream=True,
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    chunk_count = 0
    try:
        chunks = parse_stream_chunks(resp)
        chunk_count = len(chunks)
        passed = chunk_count >= 5
        detail = f"收到 {chunk_count} 个分块, 期望≥5"
    except Exception as e:
        detail = f"流式解析异常: {e}"

    suite.results.append(TestCaseResult(
        name="流式响应stream=true返回data:分块(≥5块)",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.4: 支持 system role 消息 ===
    start = time.time()
    resp = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that only responds with 'MOCK_OK'."},
            {"role": "user", "content": "hello"},
        ],
    )
    duration = (time.time() - start) * 1000

    passed = resp.status_code == 200
    detail = f"状态码: {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            detail += f", 响应内容: {content[:100]}"
        except (KeyError, IndexError):
            detail += ", 响应结构异常"
    else:
        detail += f", 错误: {resp.text[:200]}"

    suite.results.append(TestCaseResult(
        name="支持system role消息",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.5: 参数真实生效验证 ===
    # 发送 max_tokens=5 的请求，验证返回内容确实受到限制
    start = time.time()
    resp_normal = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[{"role": "user", "content": "Tell me a long story about cats"}],
        max_tokens=5,
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    if resp_normal.status_code == 200:
        data = resp_normal.json()
        try:
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            content = data["choices"][0]["message"]["content"]
            # With max_tokens=5, the response should be very short
            passed = completion_tokens <= 10 or len(content.split()) <= 10
            detail = f"completion_tokens={completion_tokens}, content_len={len(content)}, content_words={len(content.split())}"
        except (KeyError, IndexError) as e:
            detail = f"解析异常: {e}"
    else:
        detail = f"状态码: {resp_normal.status_code}"

    suite.results.append(TestCaseResult(
        name="参数真实生效验证(max_tokens=5)",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp_normal.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.6: 流式输出完整性 ===
    start = time.time()
    resp = client.chat_completions(
        model=TEST_MODEL_OPENAI,
        messages=[{"role": "user", "content": "Tell me something"}],
        stream=True,
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    try:
        chunks = parse_stream_chunks(resp)
        content = collect_stream_content(chunks)
        # Check that stream has proper structure: has finish_reason=stop in last chunk
        has_stop = False
        for chunk in chunks:
            for choice in chunk.get("choices", []):
                if choice.get("finish_reason") == "stop":
                    has_stop = True
        passed = len(content) > 0 and has_stop
        detail = f"流式内容长度: {len(content)}, finish_reason=stop: {has_stop}, chunks: {len(chunks)}"
    except Exception as e:
        detail = f"异常: {e}"

    suite.results.append(TestCaseResult(
        name="流式输出完整性(有内容且finish_reason=stop)",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.7: Claude 模型 messages 协议 ===
    start = time.time()
    resp = client.messages_api(
        model=TEST_MODEL_CLAUDE,
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=100,
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    if resp.status_code == 200:
        data = resp.json()
        try:
            # Claude protocol: response has content array with text
            content_blocks = data.get("content", [])
            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content += block.get("text", "")
            passed = bool(text_content) and data.get("type") == "message"
            detail = f"type={data.get('type')}, content_len={len(text_content)}, stop_reason={data.get('stop_reason')}"
        except Exception as e:
            detail = f"解析异常: {e}, 原始: {json.dumps(data, ensure_ascii=False)[:200]}"
    else:
        detail = f"状态码: {resp.status_code}, 响应: {resp.text[:200]}"

    suite.results.append(TestCaseResult(
        name="Claude模型messages协议兼容",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    # === Test 2.8: OpenAI responses 协议 ===
    start = time.time()
    resp = client.responses_api(
        model=TEST_MODEL_OPENAI,
        input_data=[{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
    )
    duration = (time.time() - start) * 1000

    passed = False
    detail = ""
    if resp.status_code == 200:
        data = resp.json()
        try:
            # Responses protocol: response has output array
            obj_type = data.get("object", "")
            status = data.get("status", "")
            output = data.get("output", [])
            passed = obj_type == "response" or status == "completed" or len(output) > 0
            detail = f"object={obj_type}, status={status}, output_count={len(output)}"
        except Exception as e:
            detail = f"解析异常: {e}, 原始: {json.dumps(data, ensure_ascii=False)[:200]}"
    else:
        detail = f"状态码: {resp.status_code}, 响应: {resp.text[:200]}"

    suite.results.append(TestCaseResult(
        name="OpenAI主流模型responses协议兼容",
        category="协议兼容性测试",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        detail=detail,
        duration_ms=duration,
        request_id=resp.headers.get("X-Api-Request-Id", ""),
    ))

    return suite


if __name__ == "__main__":
    result = run_protocol_tests()
    for r in result.results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name}: {r.detail}")
    print(f"\n总分: {result.total_score:.1f}/{result.max_score:.1f} 通过率: {result.pass_rate:.1%}")
