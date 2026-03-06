"""FastAPI 应用入口

提供 WebSocket 端点用于对话，REST API 用于会话管理。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import ANTHROPIC_API_KEY, SKILLS_DIR
from db.session import init_db
from utils.logger import logger

# Import API routers
from api.routers import conversations, skills, agent
from api.ws import chat

# ─── 初始化 ─────────────────────────────────────────────

app = FastAPI(title="Claude Agent Demo", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # 初始化数据库
    await init_db()

    # 初始化 PostgresSaver + PostgresStore + Agent
    from agent import init_pg

    await init_pg()

    logger.info(f"Skills 目录: {SKILLS_DIR}")
    if ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY 已配置")
    else:
        logger.warning("未设置 ANTHROPIC_API_KEY，Agent 功能不可用")

    skills_path = Path(SKILLS_DIR)
    if skills_path.exists():
        skill_dirs = [
            d.name
            for d in skills_path.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]
        logger.info(f"发现 {len(skill_dirs)} 个 Skills: {skill_dirs}")


# ─── 包含路由 ────────────────────────────────────────────

app.include_router(conversations.router)
app.include_router(skills.router)
app.include_router(agent.router)
app.include_router(chat.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(ANTHROPIC_API_KEY),
    }


# ─── 静态文件服务（生产模式） ─────────────────────────────

# FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
# if FRONTEND_DIST.exists():
#     logger.info(f"正在从目录挂载静态前端文件: {FRONTEND_DIST}")
#     app.mount(
#         "/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend"
#     )
# else:
#     logger.debug(f"未能找到前端构建目录 {FRONTEND_DIST}，将不会提供静态文件服务。")


# ─── 入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("正在 http://0.0.0.0:8000 启动 Uvicorn 服务器")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
