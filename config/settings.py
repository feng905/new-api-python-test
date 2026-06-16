# new-api-autotest 配置文件

# 被测系统
BASE_URL = "http://localhost:3000"
API_PREFIX = "/v1"

# 数据库路径（用于查询测试数据）
DB_PATH = "../new-api/one-api.db"

# 管理员凭证
ADMIN_ACCESS_TOKEN = "BBwrju4oo3pvMsDJWOfnLWwkbTMoWhQ="
ADMIN_USER_ID = "1"

# 测试用 Token（从数据库获取）
VALID_TOKEN = "uMFygPAdMBpXMHZtBPTsK2yEWr81eZWxfol7O23qr5b9B6aa"
INVALID_TOKEN = "sk-invalid-token-00000000000000000000000000000000"

# 测试模型
TEST_MODEL_OPENAI = "gpt-3.5-turbo"
TEST_MODEL_CLAUDE = "claude-opus-4-6"

# 本地模拟渠道
MOCK_CHANNEL_URL = "http://127.0.0.1:8880"
MOCK_CHANNEL_KEY = "af561a7400ef4723b164fa39a0b667b6.nfPsmyyj0sqmaw6G"

# 测试参数
CONCURRENT_TEST_COUNT = 100
RATE_LIMIT_MAX_REQUESTS = 50
RATE_LIMIT_WINDOW_SEC = 60

# 报告输出
REPORT_DIR = "./reports"
