"""
测试结果报告生成器
输出 HTML + JSON 格式的测试报告，包含得分、通过率、详细结果
"""
import json
import time
from datetime import datetime
from jinja2 import Template
from tests.base import TestCaseResult, TestSuiteResult, REPORT_DIR
import os

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>new-api 自动化测试报告</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #e8eaed; color: #202124; }
  .header { background: linear-gradient(135deg, #4285f4, #1a73e8); color: white; padding: 32px 40px; }
  .header h1 { margin: 0; font-size: 26px; }
  .header p { margin: 4px 0 0; opacity: 0.9; font-size: 14px; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .card h3 { margin: 0 0 8px; font-size: 13px; color: #5f6368; }
  .card .num { font-size: 36px; font-weight: 700; }
  .card .num.green { color: #34a853; }
  .card .num.orange { color: #fbbc04; }
  .card .num.red { color: #ea4335; }
  .card .sub { font-size: 12px; color: #80868b; margin-top: 4px; }
  .suite { background: white; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
  .suite-header { display: flex; align-items: center; padding: 16px 24px; border-bottom: 1px solid #e8eaed; }
  .suite-header h2 { margin: 0; font-size: 16px; flex: 1; }
  .suite-header .score { font-size: 14px; color: #5f6368; }
  .suite-header .score span { font-weight: 700; }
  .bar-bg { height: 6px; border-radius: 3px; background: #e8eaed; margin-top: 8px; }
  .bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
  .bar-fill.green { background: #34a853; }
  .bar-fill.orange { background: #fbbc04; }
  .bar-fill.red { background: #ea4335; }
  table { width: 100%; border-collapse: collapse; }
  th { background: #f8f9fa; padding: 10px 16px; text-align: left; font-size: 12px; color: #5f6368; font-weight: 600; border-bottom: 1px solid #e8eaed; }
  td { padding: 12px 16px; border-bottom: 1px solid #f1f3f4; font-size: 13px; vertical-align: top; }
  tr:hover { background: #f8f9fa; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .badge.ok { background: #e6f4ea; color: #137333; }
  .badge.fail { background: #fce8e6; color: #c5221f; }
  .detail { color: #5f6368; font-size: 12px; max-width: 400px; word-break: break-all; }
  .meta { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 13px; color: #5f6368; line-height: 1.8; }
  .meta strong { color: #202124; }
</style>
</head>
<body>
<div class="header">
  <h1>🧪 new-api 自动化测试报告</h1>
  <p>生成时间：{{ timestamp }} | 被测系统：{{ base_url }}</p>
</div>
<div class="container">
  <div class="meta">
    <strong>被测系统：</strong>{{ base_url }}<br>
    <strong>数据库：</strong>{{ db_path }}<br>
    <strong>测试Token：</strong>{{ token_preview }}
  </div>

  <div class="summary">
    <div class="card">
      <h3>总通过率</h3>
      <div class="num {% if pass_rate >= 0.9 %}green{% elif pass_rate >= 0.6 %}orange{% else %}red{% endif %}">{{ "%.1f"|format(pass_rate * 100) }}%</div>
      <div class="sub">{{ passed_count }}/{{ total_count }} 项通过</div>
      <div class="bar-bg"><div class="bar-fill {% if pass_rate >= 0.9 %}green{% elif pass_rate >= 0.6 %}orange{% else %}red{% endif %}" style="width: {{ pass_rate * 100 }}%"></div></div>
    </div>
    <div class="card">
      <h3>总分</h3>
      <div class="num {% if total_score / max_score >= 0.9 %}green{% elif total_score / max_score >= 0.6 %}orange{% else %}red{% endif %}">{{ "%.1f"|format(total_score) }}/{{ "%.1f"|format(max_score) }}</div>
      <div class="sub">满分 {{ "%.1f"|format(max_score) }}</div>
    </div>
    <div class="card">
      <h3>测试套件</h3>
      <div class="num" style="color: #4285f4;">{{ suite_count }}</div>
      <div class="sub">个测试维度</div>
    </div>
    <div class="card">
      <h3>总耗时</h3>
      <div class="num" style="color: #202124;">{{ "%.1f"|format(total_duration_ms / 1000) }}s</div>
      <div class="sub">毫秒</div>
    </div>
  </div>

  {% for suite in suites %}
  <div class="suite">
    <div class="suite-header">
      <h2>{{ suite.category }}</h2>
      <div class="score">
        得分 <span>{{ "%.1f"|format(suite.total_score) }}</span> / {{ "%.1f"|format(suite.max_score) }}
        <div class="bar-bg" style="width:200px;display:inline-block;vertical-align:middle;margin-left:8px;">
          <div class="bar-fill {% if suite.pass_rate >= 0.9 %}green{% elif suite.pass_rate >= 0.6 %}orange{% else %}red{% endif %}" style="width: {{ suite.pass_rate * 100 }}%"></div>
        </div>
      </div>
    </div>
    <table>
      <tr>
        <th>状态</th>
        <th>测试用例</th>
        <th>得分</th>
        <th>详情</th>
        <th>耗时(ms)</th>
        <th>Request ID</th>
      </tr>
      {% for r in suite.results %}
      <tr>
        <td><span class="badge {% if r.passed %}ok{% else %}fail{% endif %}">{{ "✅" if r.passed else "❌" }}</span></td>
        <td><strong>{{ r.name }}</strong></td>
        <td>{{ "%.1f"|format(r.score) }}/{{ "%.1f"|format(r.max_score) }}</td>
        <td class="detail">{{ r.detail }}</td>
        <td>{{ "%.1f"|format(r.duration_ms) if r.duration_ms else "-" }}</td>
        <td style="font-size:11px;color:#80868b;">{{ r.request_id[:20] if r.request_id else "-" }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endfor %}

  <div style="text-align:center;color:#80868b;font-size:12px;padding:24px;">由 new-api-autotest 自动生成 · {{ timestamp }}</div>
</div>
</body>
</html>
"""


def generate_html_report(suites, output_path, base_url="", db_path="", token=""):
    total_passed = sum(s.pass_count for s in suites)
    total_count = sum(s.total_count for s in suites)
    total_score = sum(s.total_score for s in suites)
    total_max = sum(s.max_score for s in suites)
    total_duration = sum(r.duration_ms for s in suites for r in s.results)

    context = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "db_path": db_path,
        "token_preview": token[:8] + "..." if len(token) > 8 else token,
        "suites": [{
            "category": s.category,
            "total_score": s.total_score,
            "max_score": s.max_score,
            "pass_rate": s.pass_rate,
            "pass_count": s.pass_count,
            "total_count": s.total_count,
            "results": [{
                "name": r.name,
                "passed": r.passed,
                "score": r.score,
                "max_score": r.max_score,
                "detail": r.detail,
                "duration_ms": r.duration_ms,
                "request_id": r.request_id,
            } for r in s.results],
        } for s in suites],
        "pass_rate": total_passed / total_count if total_count else 0,
        "passed_count": total_passed,
        "total_count": total_count,
        "total_score": total_score,
        "max_score": total_max,
        "suite_count": len(suites),
        "total_duration_ms": total_duration,
    }

    template = Template(HTML_TEMPLATE)
    html = template.render(**context)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def generate_json_report(suites, output_path):
    report = {
        "generated_at": datetime.now().isoformat(),
        "suites": [{
            "category": s.category,
            "total_score": s.total_score,
            "max_score": s.max_score,
            "pass_rate": s.pass_rate,
            "pass_count": s.pass_count,
            "total_count": s.total_count,
            "results": [{
                "name": r.name,
                "category": r.category,
                "passed": r.passed,
                "score": r.score,
                "max_score": r.max_score,
                "detail": r.detail,
                "duration_ms": r.duration_ms,
                "request_id": r.request_id,
            } for r in s.results],
        } for s in suites],
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return output_path


if __name__ == "__main__":
    # 单独运行报告生成器（演示）
    dummy_suite = TestSuiteResult(category="演示套件")
    dummy_suite.results.append(TestCaseResult(name="演示测试", category="演示", passed=True, score=1.0, max_score=1.0, detail="演示详情"))
    generate_html_report([dummy_suite], "/tmp/test_report.html", "http://localhost:3000", "/tmp/test.db", "sk-demo")
    print("演示报告已生成：/tmp/test_report.html")
