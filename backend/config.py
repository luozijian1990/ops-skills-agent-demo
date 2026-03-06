"""配置模块"""

import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

# 项目 backend 根目录
BASE_DIR = Path(__file__).resolve().parent

# 显式加载 backend/.env，避免因启动目录不同导致变量未加载
load_dotenv(BASE_DIR / ".env")

# API Key（claude-agent-sdk 会自动从环境变量读取，这里保留用于健康检查）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 项目根目录 (由于是前后端分离，限制只在 backend 内)
PROJECT_DIR = str(BASE_DIR)

# Skills 目录
SKILLS_DIR = str(BASE_DIR / "skills")

# Agent 配置
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-5-20250929")
MAX_TURNS = int(os.getenv("MAX_TURNS", "10"))

# ─── PostgreSQL 配置 ──────────────────────────────────
DB_IP = os.getenv("DB_IP", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "30306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "claude_agent")

# SQLAlchemy 异步连接串 (asyncpg 驱动)
DATABASE_URL = f"postgresql+asyncpg://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@{DB_IP}:{DB_PORT}/{DB_NAME}"

# psycopg 同步连接串 (PostgresSaver / PostgresStore 用)
DATABASE_URL_SYNC = f"postgresql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@{DB_IP}:{DB_PORT}/{DB_NAME}"

# ─── 日志配置 ────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))
LOG_MAX_SIZE_MB = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
