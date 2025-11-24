from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from models.database import (
    create_persona,
    delete_persona,
    get_persona_by_id,
    get_preset_personas,
    update_persona,
)

router = APIRouter()


class PersonaCreate(BaseModel):
    """创建人设请求模型"""

    name: str
    persona_type: str
    style: str
    target_audience: str
    characteristics: str
    tone: str
    keywords: List[str] = []


class PersonaUpdate(BaseModel):
    """更新人设请求模型"""

    name: Optional[str] = None
    persona_type: Optional[str] = None
    style: Optional[str] = None
    target_audience: Optional[str] = None
    characteristics: Optional[str] = None
    tone: Optional[str] = None
    keywords: Optional[List[str]] = None


class PersonaResponse(BaseModel):
    """人设响应模型"""

    id: str
    name: str
    persona_type: str
    style: str
    target_audience: str
    characteristics: str
    tone: str
    keywords: List[str]
    is_preset: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_db(cls, persona: dict):
        """从数据库数据创建响应对象，处理类型转换"""
        # 处理 keywords：如果是字符串，分割成列表
        keywords = persona.get("keywords", "")
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        # 处理时间字段：转换 datetime 为 ISO 格式字符串
        created_at = persona.get("created_at")
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()

        updated_at = persona.get("updated_at")
        if hasattr(updated_at, 'isoformat'):
            updated_at = updated_at.isoformat()

        return cls(
            id=persona["id"],
            name=persona["name"],
            persona_type=persona["persona_type"],
            style=persona["style"],
            target_audience=persona["target_audience"],
            characteristics=persona["characteristics"],
            tone=persona["tone"],
            keywords=keywords,
            is_preset=persona.get("is_preset", False),
            created_at=created_at,
            updated_at=updated_at
        )


@router.post("/", response_model=PersonaResponse)
async def create_persona_endpoint(persona_data: PersonaCreate):
    """创建人设"""
    try:
        persona_dict = {
            "name": persona_data.name,
            "persona_type": persona_data.persona_type,
            "style": persona_data.style,
            "target_audience": persona_data.target_audience,
            "characteristics": persona_data.characteristics,
            "tone": persona_data.tone,
            "keywords": ",".join(persona_data.keywords) if persona_data.keywords else "",
            "is_preset": False,  # 默认为非预设人设
        }

        persona = await create_persona(persona_dict)
        if not persona:
            raise HTTPException(status_code=500, detail="人设创建失败")
        return PersonaResponse.from_db(persona)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建人设失败: {str(e)}")


@router.get("/", response_model=List[PersonaResponse])
async def get_personas():
    """获取所有人设列表（主要是预设人设）"""
    try:
        personas = await get_preset_personas()
        return [PersonaResponse.from_db(persona) for persona in personas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人设列表失败: {str(e)}")


@router.get("/preset", response_model=List[PersonaResponse])
async def get_preset_personas_list():
    """获取预设人设列表"""
    try:
        personas = await get_preset_personas()
        return [PersonaResponse.from_db(persona) for persona in personas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预设人设失败: {str(e)}")


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona_by_id(persona_id: str, persona_data: PersonaUpdate):
    """更新人设"""
    try:
        persona = await get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")

        # 预设人设不允许修改
        if persona.get("is_preset", False):
            raise HTTPException(status_code=403, detail="不能修改预设人设")

        update_dict = {
            k: v for k, v in persona_data.model_dump().items() if v is not None
        }
        updated_persona = await update_persona(persona_id, update_dict)

        if not updated_persona:
            raise HTTPException(status_code=500, detail="更新人设失败")

        return PersonaResponse.from_db(updated_persona)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新人设失败: {str(e)}")


@router.delete("/{persona_id}")
async def delete_persona_by_id(persona_id: str):
    """删除人设"""
    try:
        persona = await get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")

        # 预设人设不允许删除
        if persona.get("is_preset", False):
            raise HTTPException(status_code=403, detail="不能删除预设人设")

        success = await delete_persona(persona_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除人设失败")

        return {"message": "人设删除成功", "persona_id": persona_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除人设失败: {str(e)}")


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona_by_id_endpoint(persona_id: str):
    """根据ID获取人设详情"""
    try:
        persona = await get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")

        return PersonaResponse(**persona)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人设失败: {str(e)}")
