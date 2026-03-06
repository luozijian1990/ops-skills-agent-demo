from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import SKILLS_DIR
from utils.logger import logger

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills():
    """返回已加载的 Skills 列表"""
    logger.info("正在获取可用技能(Skills)列表")
    skills_path = Path(SKILLS_DIR)
    if not skills_path.exists():
        logger.warning(f"Skills 目录 {SKILLS_DIR} 不存在")
        return JSONResponse([])

    skills = []
    for d in sorted(skills_path.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            try:
                content = (d / "SKILL.md").read_text(encoding="utf-8")
                name = d.name
                description = ""
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        for line in parts[1].strip().split("\n"):
                            if line.startswith("name:"):
                                name = (
                                    line.split(":", 1)[1].strip().strip('"').strip("'")
                                )
                            elif line.startswith("description:"):
                                description = (
                                    line.split(":", 1)[1].strip().strip('"').strip("'")
                                )
                skills.append({"name": name, "description": description})
            except Exception as e:
                logger.error(f"解析技能 {d.name} 时出错: {e}")
                skills.append({"name": d.name, "description": ""})

    logger.debug(f"成功加载了 {len(skills)} 个技能")
    return JSONResponse(skills)
