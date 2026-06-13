#!/usr/bin/env python3
"""
读取 run_tests.py 生成的 JSON 结果，生成 HTML 报告
用法：python3 generate_report.py <json_file_path>
"""
import sys
import os
import json
import webbrowser
from datetime import datetime

def load_results(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def group_by_category(results):
    suites = {}
    for r in results:
        cat = r.get("category", "未知")
        if cat not in suites:
            suites[cat] = []
        suites[cat].append(r)
    return suites


def render_html(report_data, output_path):
    results = report_data.get("results", [])
    base_url = report_data.get("base_url", "")
    suites = group_by_category(results)

    total_pass = sum(1 for r in results if r.get("passed"))
    total_cnt = len(results)
    total_score = sum(r.get("score", 0) for r in results)
    total_max = sum(r.get("max_score", 1) for r in results)
    pass_rate = total_pass / total_cnt if total_cnt else 0

    # 颜色判断
    def color_class(rate):
        if rate >= 0.9:
            return "green"
        elif rate >= 0.6:
            return "orange"
        return "red"

    def bar_hex(rate):
        if rate >= 0.9:
            return "#34a853"
        elif rate >= 0.6:
            return "#fbbc04"
        return "#ea4335"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = []
    html.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>new-api 测试报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:#f0f2f5;color:#1d1d1f;line-height:1.5;-webkit-font-smoothing:antialiased;}}
.header{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:48px 40px 40px;position:relative;overflow:hidden;}}
.header::before{{content:'';position:absolute;top:-50%;right:-20%;width:500px;height:500px;border-radius:50%;background:rgba(255,255,255,0.05);}}
.header::after{{content:'';position:absolute;bottom:-60%;left:-10%;width:400px;height:400px;border-radius:50%;background:rgba(255,255,255,0.03);}}
.header-content{{position:relative;z-index:1;max-width:1200px;margin:0 auto;}}
.header h1{{font-size:28px;font-weight:700;color:white;letter-spacing:-0.5px;}}
.header .subtitle{{font-size:14px;color:rgba(255,255,255,0.75);margin-top:8px;}}
.header .subtitle span{{display:inline-flex;align-items:center;gap:4px;margin-right:16px;}}

.container{{max-width:1200px;margin:-24px auto 0;padding:0 24px 48px;position:relative;z-index:2;}}

.meta-bar{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px;background:white;border-radius:16px;padding:16px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);font-size:13px;color:#6e6e73;}}
.meta-bar .tag{{display:inline-flex;align-items:center;gap:6px;background:#f5f5f7;padding:6px 12px;border-radius:8px;}}
.meta-bar .tag svg{{width:14px;height:14px;opacity:0.5;}}
.meta-bar .tag strong{{color:#1d1d1f;}}

.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:32px;}}

.card{{background:white;border-radius:16px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);transition:transform 0.2s,box-shadow 0.2s;position:relative;overflow:hidden;}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,0.1);}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
.card.green::before{{background:linear-gradient(90deg,#34a853,#4caf50);}}
.card.orange::before{{background:linear-gradient(90deg,#f9a825,#ffca28);}}
.card.red::before{{background:linear-gradient(90deg,#ea4335,#f44336);}}
.card.blue::before{{background:linear-gradient(90deg,#4285f4,#667eea);}}
.card.dark::before{{background:linear-gradient(90deg,#5f6368,#80868b);}}

.card .label{{font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;}}
.card .num{{font-size:38px;font-weight:700;letter-spacing:-1px;line-height:1;}}
.card .num.green{{color:#34a853;}}
.card .num.orange{{color:#f9a825;}}
.card .num.red{{color:#ea4335;}}
.card .num.blue{{color:#4285f4;}}
.card .num.dark{{color:#1d1d1f;}}
.card .sub{{font-size:12px;color:#86868b;margin-top:8px;}}

.progress{{margin-top:12px;height:6px;border-radius:3px;background:#f0f0f0;overflow:hidden;}}
.progress-fill{{height:100%;border-radius:3px;transition:width 0.6s ease;}}
.progress-fill.green{{background:linear-gradient(90deg,#34a853,#66bb6a);}}
.progress-fill.orange{{background:linear-gradient(90deg,#f9a825,#ffca28);}}
.progress-fill.red{{background:linear-gradient(90deg,#ea4335,#ef5350);}}

.suite{{background:white;border-radius:16px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04);overflow:hidden;transition:box-shadow 0.2s;}}
.suite:hover{{box-shadow:0 4px 12px rgba(0,0,0,0.08);}}

.suite-header{{display:flex;align-items:center;padding:20px 24px;gap:16px;border-bottom:1px solid #f0f0f0;}}
.suite-header h2{{font-size:16px;font-weight:600;color:#1d1d1f;flex:1;}}
.suite-stats{{display:flex;align-items:center;gap:12px;}}
.suite-stats .score-badge{{background:#f5f5f7;padding:4px 12px;border-radius:8px;font-size:13px;color:#6e6e73;white-space:nowrap;}}
.suite-stats .score-badge strong{{color:#1d1d1f;}}
.suite-stats .rate-mini{{width:80px;height:5px;border-radius:3px;background:#f0f0f0;overflow:hidden;}}
.suite-stats .rate-mini-fill{{height:100%;border-radius:3px;}}

table{{width:100%;border-collapse:collapse;}}
thead th{{background:#fafafa;padding:12px 16px;text-align:left;font-size:11px;color:#86868b;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #f0f0f0;position:sticky;top:0;}}
tbody td{{padding:14px 16px;border-bottom:1px solid #f8f8f8;font-size:13px;vertical-align:middle;}}
tbody tr{{transition:background 0.15s;}}
tbody tr:hover{{background:#fafbfc;}}
tbody tr:last-child td{{border-bottom:none;}}

.badge{{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:0.3px;}}
.badge.ok{{background:#e6f4ea;color:#137333;}}
.badge.ok::before{{content:'✓';font-weight:700;}}
.badge.fail{{background:#fce8e6;color:#c5221f;}}
.badge.fail::before{{content:'✗';font-weight:700;}}

.detail{{color:#6e6e73;font-size:12px;max-width:360px;word-break:break-all;line-height:1.6;font-family:'SF Mono',Monaco,'Cascadia Code',monospace;background:#f8f8fa;padding:6px 10px;border-radius:6px;border:1px solid #f0f0f2;}}
.request-id{{font-size:11px;color:#aeaeb2;font-family:'SF Mono',Monaco,monospace;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}

.footer{{text-align:center;color:#aeaeb2;font-size:12px;padding:32px 24px;}}

@media(max-width:768px){{
  .header{{padding:32px 20px 28px;}}
  .container{{padding:0 16px 32px;}}
  .summary{{grid-template-columns:repeat(2,1fr);gap:12px;}}
  .card{{padding:16px;}}
  .card .num{{font-size:28px;}}
  .suite-header{{flex-direction:column;align-items:flex-start;gap:8px;}}
  table{{font-size:12px;}}
  th,td{{padding:10px 12px !important;}}
}}

@media print{{
  body{{background:white;}}
  .header{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
  .card:hover,.suite:hover{{transform:none;box-shadow:0 1px 3px rgba(0,0,0,0.06);}}
}}
</style>
</head>
<body>
<div class="header">
  <div class="header-content">
    <h1>🧪 自动化测试报告</h1>
    <div class="subtitle">
      <span>📅 {now}</span>
      <span>🔗 {base_url}</span>
    </div>
  </div>
</div>
<div class="container">
'''.format(now=now, base_url=base_url or "N/A"))

    # Meta bar
    json_file = os.path.basename(report_data.get("_json_path", ""))
    html.append('  <div class="meta-bar">')
    html.append('    <div class="tag"><strong>被测系统</strong> {}</div>'.format(base_url or "N/A"))
    html.append('    <div class="tag"><strong>结果文件</strong> {}</div>'.format(json_file))
    html.append('    <div class="tag"><strong>通过率</strong> {:.1%}（{} / {}）</div>'.format(
        pass_rate, total_pass, total_cnt))
    html.append('  </div>')

    # Summary cards
    card_color = color_class(pass_rate)
    sc_color = color_class(total_score / total_max) if total_max else "red"

    html.append('  <div class="summary">')

    # Pass rate card
    html.append('    <div class="card {}">'.format(card_color))
    html.append('      <div class="label">总通过率</div>')
    html.append('      <div class="num {}">{:.1%}</div>'.format(card_color, pass_rate))
    html.append('      <div class="sub">{} / {} 项通过</div>'.format(total_pass, total_cnt))
    html.append('      <div class="progress"><div class="progress-fill {}" style="width:{:.0f}%"></div></div>'.format(
        card_color, pass_rate * 100))
    html.append('    </div>')

    # Score card
    html.append('    <div class="card {}">'.format(sc_color))
    html.append('      <div class="label">总得分</div>')
    html.append('      <div class="num {}">{:.1f}<span style="font-size:18px;color:#86868b;font-weight:400;"> / {:.1f}</span></div>'.format(
        sc_color, total_score, total_max))
    html.append('      <div class="sub">满分 {:.1f}</div>'.format(total_max))
    sc_rate = (total_score / total_max) if total_max else 0
    html.append('      <div class="progress"><div class="progress-fill {}" style="width:{:.0f}%"></div></div>'.format(
        sc_color, sc_rate * 100))
    html.append('    </div>')

    # Test count card
    html.append('    <div class="card blue">')
    html.append('      <div class="label">测试用例</div>')
    html.append('      <div class="num blue">{}</div>'.format(total_cnt))
    html.append('      <div class="sub">{} 个测试维度</div>'.format(len(suites)))
    html.append('    </div>')

    # Duration card
    total_duration_ms = sum(r.get("duration_ms", 0) or 0 for r in results)
    html.append('    <div class="card dark">')
    html.append('      <div class="label">总耗时</div>')
    if total_duration_ms >= 1000:
        html.append('      <div class="num dark">{:.1f}<span style="font-size:16px;color:#86868b;font-weight:400;"> s</span></div>'.format(
            total_duration_ms / 1000))
    else:
        html.append('      <div class="num dark">{:.0f}<span style="font-size:16px;color:#86868b;font-weight:400;"> ms</span></div>'.format(
            total_duration_ms))
    html.append('      <div class="sub">共 {} 项测试</div>'.format(total_cnt))
    html.append('    </div>')

    html.append('  </div>')

    # Suites
    for cat, items in suites.items():
        cat_pass = sum(1 for r in items if r.get("passed"))
        cat_total = len(items)
        cat_score = sum(r.get("score", 0) for r in items)
        cat_max = sum(r.get("max_score", 1) for r in items)
        cat_rate = cat_pass / cat_total if cat_total else 0
        html.append('  <div class="suite">')
        html.append('    <div class="suite-header">')
        html.append('      <h2>{}</h2>'.format(cat))
        html.append('      <div class="suite-stats">')
        html.append('        <div class="score-badge"><strong>{:.1f}</strong> / {:.1f}</div>'.format(
            cat_score, cat_max))
        html.append('        <div class="rate-mini"><div class="rate-mini-fill" style="width:{:.0f}%;background:{};"></div></div>'.format(
            cat_rate * 100, bar_hex(cat_rate)))
        html.append('      </div>')
        html.append('    </div>')
        html.append('    <table>')
        html.append('      <thead><tr><th style="width:60px;">状态</th><th>测试用例</th><th style="width:100px;">得分</th>'
                     '<th>详情</th><th style="width:80px;">耗时</th><th style="width:160px;">Request ID</th></tr></thead>')
        html.append('      <tbody>')
        for r in items:
            passed = r.get("passed", False)
            badge = "ok" if passed else "fail"
            html.append('        <tr>')
            html.append('          <td><span class="badge {}"></span></td>'.format(badge))
            html.append('          <td><strong>{}</strong></td>'.format(r.get("name", "")))
            html.append('          <td>{:.1f} / {:.1f}</td>'.format(
                r.get("score", 0), r.get("max_score", 1)))
            html.append('          <td><div class="detail">{}</div></td>'.format(r.get("detail", "")))
            dur = r.get("duration_ms")
            if dur is not None and dur != "":
                if float(dur) >= 1000:
                    html.append('          <td>{:.1f}s</td>'.format(float(dur) / 1000))
                else:
                    html.append('          <td>{:.0f}ms</td>'.format(float(dur)))
            else:
                html.append('          <td>-</td>')
            rid = r.get("request_id", "") or ""
            html.append('          <td><div class="request-id" title="{}">{}</div></td>'.format(
                rid, rid[:24] if rid else "-"))
            html.append('        </tr>')
        html.append('      </tbody>')
        html.append('    </table>')
        html.append('  </div>')

    html.append('  <div class="footer">由 new-api-autotest 自动生成 · {}</div>'.format(now))
    html.append('</div>')
    html.append('</body>')
    html.append('</html>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    return output_path


def main():
    if len(sys.argv) < 2:
        # 自动查找最新的 JSON 文件
        report_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports")
        if not os.path.isdir(report_dir):
            print("用法：python3 generate_report.py <json_file_path>")
            sys.exit(1)
        files = sorted(
            [os.path.join(report_dir, f) for f in os.listdir(report_dir)
             if f.endswith(".json")],
            key=os.path.getmtime, reverse=True)
        if not files:
            print("未找到 JSON 结果文件，请先运行 run_tests.py")
            sys.exit(1)
        json_path = files[0]
        print("自动使用最新结果文件：{}".format(json_path))
    else:
        json_path = sys.argv[1]

    if not os.path.isfile(json_path):
        print("文件不存在：{}".format(json_path))
        sys.exit(1)

    report_data = load_results(json_path)
    report_data["_json_path"] = json_path

    base = os.path.splitext(json_path)[0]
    output_path = base + ".html"

    render_html(report_data, output_path)
    print("HTML 报告已生成：{}".format(output_path))

    try:
        webbrowser.open("file://{}".format(os.path.abspath(output_path)))
        print("已在浏览器中打开报告")
    except Exception:
        print("请手动打开：{}".format(output_path))


if __name__ == "__main__":
    main()
