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

    def bar_color(rate):
        if rate >= 0.9:
            return "#34a853"
        elif rate >= 0.6:
            return "#fbbc04"
        return "#ea4335"

    html = []
    html.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>')
    html.append('<meta charset="UTF-8">')
    html.append('<title>new-api 自动化测试报告</title>')
    html.append('<style>')
    html.append('body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:0;background:#e8eaed;color:#202124;}}')
    html.append('.header{{background:linear-gradient(135deg,#4285f4,#1a73e8);color:white;padding:32px 40px;}}')
    html.append('.header h1{{margin:0;font-size:26px;}}')
    html.append('.header p{{margin:4px 0 0;opacity:0.9;font-size:14px;}}')
    html.append('.container{{max-width:1200px;margin:0 auto;padding:24px;}}')
    html.append('.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:32px;}}')
    html.append('.card{{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}}')
    html.append('.card h3{{margin:0 0 8px;font-size:13px;color:#5f6368;}}')
    html.append('.card .num{{font-size:36px;font-weight:700;}}')
    html.append('.card .sub{{font-size:12px;color:#80868b;margin-top:4px;}}')
    html.append('.bar-bg{{height:6px;border-radius:3px;background:#e8eaed;margin-top:8px;width:200px;display:inline-block;vertical-align:middle;margin-left:8px;}}')
    html.append('.bar-fill{{height:100%;border-radius:3px;}}')
    html.append('.suite{{background:white;border-radius:12px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;}}')
    html.append('.suite-header{{display:flex;align-items:center;padding:16px 24px;border-bottom:1px solid #e8eaed;}}')
    html.append('.suite-header h2{{margin:0;font-size:16px;flex:1;}}')
    html.append('table{{width:100%;border-collapse:collapse;}}')
    html.append('th{{background:#f8f9fa;padding:10px 16px;text-align:left;font-size:12px;color:#5f6368;font-weight:600;border-bottom:1px solid #e8eaed;}}')
    html.append('td{{padding:12px 16px;border-bottom:1px solid #f1f3f4;font-size:13px;vertical-align:top;}}')
    html.append('tr:hover{{background:#f8f9fa;}}')
    html.append('.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;}}')
    html.append('.badge.ok{{background:#e6f4ea;color:#137333;}}')
    html.append('.badge.fail{{background:#fce8e6;color:#c5221f;}}')
    html.append('.detail{{color:#5f6368;font-size:12px;max-width:400px;word-break:break-all;}}')
    html.append('.meta{{background:white;border-radius:12px;padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1);font-size:13px;color:#5f6368;line-height:1.8;}}')
    html.append('.meta strong{{color:#202124;}}')
    html.append('</style>\n</head>\n<body>')

    # Header
    html.append('<div class="header">')
    html.append('  <h1>new-api 自动化测试报告</h1>')
    html.append('  <p>生成时间：{} | 被测系统：{}</p>'.format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), base_url or "N/A"))
    html.append('</div>')

    html.append('<div class="container">')

    # Meta
    html.append('<div class="meta">')
    html.append('<strong>被测系统：</strong>{}<br>'.format(base_url or "N/A"))
    html.append('<strong>JSON 结果：</strong>{}<br>'.format(
        os.path.basename(report_data.get("_json_path", ""))))
    html.append('</div>')

    # Summary cards
    html.append('<div class="summary">')

    card_color = color_class(pass_rate)
    html.append('<div class="card">')
    html.append('  <h3>总通过率</h3>')
    html.append('  <div class="num {}">{:.1%}</div>'.format(
        card_color, pass_rate))
    html.append('  <div class="sub">{}/{} 项通过</div>'.format(
        total_pass, total_cnt))
    html.append('  <div class="bar-bg"><div class="bar-fill {}" style="width:{}%"></div></div>'.format(
        card_color, int(pass_rate * 100)))
    html.append('</div>')

    html.append('<div class="card">')
    html.append('  <h3>总分</h3>')
    sc_color = color_class(total_score / total_max) if total_max else 0
    html.append('  <div class="num {}">{:.1f}/{:.1f}</div>'.format(
        sc_color, total_score, total_max))
    html.append('  <div class="sub">满分 {:.1f}</div>'.format(total_max))
    html.append('</div>')

    html.append('<div class="card">')
    html.append('  <h3>测试用例</h3>')
    html.append('  <div class="num" style="color:#4285f4;">{}</div>'.format(total_cnt))
    html.append('  <div class="sub">个测试项</div>')
    html.append('</div>')

    html.append('</div>')  # end summary

    # Suites
    for cat, items in suites.items():
        cat_pass = sum(1 for r in items if r.get("passed"))
        cat_total = len(items)
        cat_score = sum(r.get("score", 0) for r in items)
        cat_max = sum(r.get("max_score", 1) for r in items)
        cat_rate = cat_pass / cat_total if cat_total else 0
        cc = color_class(cat_rate)

        html.append('<div class="suite">')
        html.append('  <div class="suite-header">')
        html.append('    <h2>{}</h2>'.format(cat))
        html.append('    <div class="score">得分 <span>{:.1f}</span> / {:.1f}</div>'.format(
            cat_score, cat_max))
        html.append('    <div class="bar-bg"><div class="bar-fill {}" style="width:{}%"></div></div>'.format(
            cc, int(cat_rate * 100)))
        html.append('  </div>')
        html.append('  <table>')
        html.append('    <tr><th>状态</th><th>测试用例</th><th>得分</th>'
                   '<th>详情</th><th>耗时(ms)</th><th>Request ID</th></tr>')
        for r in items:
            passed = r.get("passed", False)
            badge = "ok" if passed else "fail"
            icon = "&#10004;" if passed else "&#10008;"
            html.append('    <tr>')
            html.append('      <td><span class="badge {}">{}</span></td>'.format(
                badge, icon))
            html.append('      <td><strong>{}</strong></td>'.format(
                r.get("name", "")))
            html.append('      <td>{:.1f}/{:.1f}</td>'.format(
                r.get("score", 0), r.get("max_score", 1)))
            html.append('      <td class="detail">{}</td>'.format(
                r.get("detail", "")))
            dur = r.get("duration_ms")
            if dur is not None and dur != "":
                html.append('      <td>{:.0f}</td>'.format(float(dur)))
            else:
                html.append('      <td>-</td>')
            rid = r.get("request_id", "") or ""
            html.append('      <td style="font-size:11px;color:#80868b;">{}</td>'.format(
                rid[:24] if rid else "-"))
            html.append('    </tr>')
        html.append('  </table>')
        html.append('</div>')

    html.append('<div style="text-align:center;color:#80868b;font-size:12px;padding:24px;">'
               '由 new-api-autotest 自动生成 · {}</div>'.format(
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    html.append('</div>')  # end container
    html.append('</body>\n</html>')

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
