"""
覆盖以下测试维度：
1. 连通性与鉴权测试
2. 协议兼容性测试
3. 稳定性与限流测试
4. 异常容错测试
5. request_id 透传测试

"""

```使用方式

cp .env.example .env

pip3 install -r requirements.txt
python3 run_tests.py

测试结果保存在 test_results.json 文件中
使用python3 generate_report.py test_results.json 生成测试报告

```