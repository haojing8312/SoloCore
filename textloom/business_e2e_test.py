#!/usr/bin/env python3
"""
TextLoom 业务穿越测试脚本
测试完整的业务流程：任务创建 → 视频生成
"""

import argparse
import asyncio
import json
import mimetypes
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.enhanced_logging import (
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
)

# 测试配置
BASE_URL = "http://localhost:48095"
API_KEY = "bda38eb13ae2eaffd1cbbfb050f288e1de3ed5985873b157795d03a5f675959c"  # demo_client API key
# 仅目录模式


class BusinessTestRunner:
    """业务测试运行器"""

    def __init__(
        self,
        base_url: str = BASE_URL,
        script_style: str = "default",
        local_dir: Optional[str] = None,
        desc_json: Optional[str] = None,
    ):
        self.base_url = base_url
        self.script_style = script_style
        self.local_dir = local_dir
        self.client = None
        self.persona_id = None
        self.task_id = None
        self.test_results = []
        # 文件名 -> 描述 映射（用于生成 media_meta）
        self.desc_by_name: Dict[str, str] = {}
        try:
            if desc_json:
                desc_path = Path(desc_json)
                if desc_path.exists():
                    with open(desc_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            # 仅保留字符串描述
                            self.desc_by_name = {
                                str(k): str(v)
                                for k, v in data.items()
                                if isinstance(v, (str, int, float))
                            }
                        elif isinstance(data, list):
                            # 支持列表 [{"filename":"a.mp4","description":"..."}]
                            tmp: Dict[str, str] = {}
                            for item in data:
                                if isinstance(item, dict):
                                    fn = str(item.get("filename") or "").strip()
                                    ds = str(item.get("description") or "").strip()
                                    if fn and ds:
                                        tmp[fn] = ds
                            self.desc_by_name = tmp
                if self.desc_by_name:
                    log_error(
                        f"📝 已加载描述映射 {len(self.desc_by_name)} 条，用于构建 media_meta"
                    )
        except Exception as e:
            log_error(f"⚠️  描述文件解析失败（忽略）：{e}")

    async def __aenter__(self):
        # 设置API密钥认证头
        headers = {"X-API-Key": API_KEY}
        self.client = httpx.AsyncClient(timeout=60.0, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def log_result(self, step: str, success: bool, message: str, data: Any = None):
        """记录测试结果"""
        result = {
            "step": step,
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        log_info(f"{status} {step}: {message}")
        if data and success:
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
            log_info(f"   数据: {data_str}")
        elif not success and data:
            log_error(f"   错误详情: {data}")
        log_info()

    async def test_api_health(self) -> bool:
        """测试API健康状态"""
        log_info("=" * 60)
        log_info("步骤 0: API健康检查")
        log_info("=" * 60)

        try:
            # 检查根端点
            response = await self.client.get(f"{self.base_url}/")

            if response.status_code == 200:
                root_data = response.json()
                self.log_result("API根端点", True, "API服务正常运行", root_data)
            else:
                self.log_result(
                    "API根端点",
                    False,
                    f"API服务异常: {response.status_code}",
                    response.text,
                )
                return False

            # 检查健康端点
            response = await self.client.get(f"{self.base_url}/health")

            if response.status_code == 200:
                health_data = response.json()
                self.log_result("健康检查", True, "API健康状态良好", health_data)
                return True
            else:
                self.log_result(
                    "健康检查",
                    False,
                    f"健康检查失败: {response.status_code}",
                    response.text,
                )
                return False

        except Exception as e:
            self.log_result("API健康检查", False, f"健康检查异常: {str(e)}")
            return False

    async def test_persona_management(self) -> bool:
        """测试人设管理"""
        log_info("=" * 60)
        log_info("步骤 4: 人设管理测试")
        log_info("=" * 60)

        # 4.1 创建人设
        persona_data = {
            "name": "科技博主小A",
            "persona_type": "教育",
            "style": "专业科普",
            "target_audience": "技术爱好者",
            "characteristics": "擅长用通俗易懂的语言解释复杂的技术概念，语言风格活泼有趣，经常使用类比和实例",
            "tone": "轻松专业，富有活力",
            "keywords": ["AI", "机器学习", "技术科普", "创新", "实践"],
        }

        try:
            # 创建人设
            response = await self.client.post(
                f"{self.base_url}/personas/", json=persona_data
            )

            if response.status_code == 200:
                persona_result = response.json()
                self.persona_id = persona_result.get("id")

                self.log_result(
                    "创建人设",
                    True,
                    f"人设创建成功，ID: {self.persona_id}",
                    persona_result,
                )
            else:
                self.log_result(
                    "创建人设",
                    False,
                    f"创建失败: {response.status_code}",
                    response.text,
                )
                return False

            # 4.2 获取人设列表
            response = await self.client.get(f"{self.base_url}/personas/")

            if response.status_code == 200:
                personas = response.json()
                self.log_result(
                    "获取人设列表",
                    True,
                    f"获取成功，共{len(personas)}个人设",
                    {"count": len(personas), "personas": [p["name"] for p in personas]},
                )
            else:
                self.log_result(
                    "获取人设列表",
                    False,
                    f"获取失败: {response.status_code}",
                    response.text,
                )
                return False

            # 4.3 获取预设人设
            response = await self.client.get(f"{self.base_url}/personas/presets")

            if response.status_code == 200:
                presets = response.json()
                self.log_result(
                    "获取预设人设",
                    True,
                    f"获取成功，共{len(presets)}个预设人设",
                    {"count": len(presets)},
                )
            else:
                self.log_result(
                    "获取预设人设",
                    False,
                    f"获取失败: {response.status_code}",
                    response.text,
                )

            return True

        except Exception as e:
            self.log_result("人设管理", False, f"人设管理异常: {str(e)}")
            return False

    # 已移除单文件与远程URL模式

    async def test_create_video_task(self) -> bool:
        """测试创建视频任务：仅目录模式（批量上传）"""
        log_info("=" * 60)
        log_info(f"步骤 5: 创建文本转视频任务 (脚本风格: {self.script_style})")
        log_info("=" * 60)

        try:
            media_urls: List[str] = []
            title: str = "自动创建任务"

            # 目录模式：批量上传
            dir_path = Path(self.local_dir)
            if not dir_path.exists() or not dir_path.is_dir():
                self.log_result("创建视频任务", False, f"目录不存在: {self.local_dir}")
                return False
            title = dir_path.name
            all_files = [p for p in dir_path.rglob("*") if p.is_file()]
            if not all_files:
                self.log_result(
                    "创建视频任务", False, f"目录内无文件: {self.local_dir}"
                )
                return False
            if len(all_files) > 50:
                log_warning(
                    f"⚠️  目录包含 {len(all_files)} 个文件，仅取前50个以满足接口限制"
                )
            to_upload = all_files[:50]

            multipart_files = []
            for p in to_upload:
                mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
                multipart_files.append(("files", (p.name, open(p, "rb"), mime)))

            upload_resp = await self.client.post(
                f"{self.base_url}/tasks/attachments/upload", files=multipart_files
            )
            for _, (_, fh, _) in multipart_files:
                try:
                    fh.close()
                except Exception:
                    pass
            if upload_resp.status_code != 200:
                self.log_result(
                    "上传附件",
                    False,
                    f"上传失败: HTTP {upload_resp.status_code}",
                    upload_resp.text,
                )
                return False
            upload_data = upload_resp.json()
            self.log_result("上传附件", True, "附件上传返回", upload_data)
            items = upload_data.get("items", [])
            media_urls = [
                it.get("url") for it in items if it.get("success") and it.get("url")
            ]
            if not media_urls:
                self.log_result(
                    "创建视频任务", False, "无可用URL用于创建任务", upload_data
                )
                return False

            # 构建 media_meta（url -> description），按返回的 filename 匹配本地描述映射
            media_meta_map: Dict[str, str] = {}
            try:
                if self.desc_by_name:
                    for it in items:
                        if not (it.get("success") and it.get("url")):
                            continue
                        fn = it.get("filename") or ""
                        # 仅给视频加描述（若需要只针对视频）
                        if it.get("media_type") == "video" and fn in self.desc_by_name:
                            media_meta_map[it["url"]] = self.desc_by_name[fn]
                    if media_meta_map:
                        log_error(
                            f"🧩 已为 {len(media_meta_map)} 个视频匹配到人工描述，将作为 media_meta 传入任务创建"
                        )
            except Exception as _:
                pass

            # 创建任务（multipart form，避免 httpx 旧版本对 data=list[tuple] 的兼容问题）
            files_form = [
                ("title", (None, title)),
                ("mode", (None, "multi_scene")),
                ("script_style", (None, self.script_style)),
                ("multi_video_count", (None, "3")),
            ] + [("media_urls", (None, u)) for u in media_urls]

            # 追加 media_meta（可选）
            if media_meta_map:
                files_form.append(
                    (
                        "media_meta",
                        (None, json.dumps(media_meta_map, ensure_ascii=False)),
                    )
                )

            create_resp = await self.client.post(
                f"{self.base_url}/tasks/create-video-task", files=files_form
            )

            if create_resp.status_code == 200:
                task_data = create_resp.json()
                self.task_id = task_data.get("id")
                if not self.task_id:
                    self.log_result(
                        "创建视频任务", False, "任务创建响应中缺少任务ID", task_data
                    )
                    return False
                self.log_result(
                    "创建视频任务", True, f"任务创建成功，ID: {self.task_id}", task_data
                )
                await asyncio.sleep(1)
                try:
                    status_response = await self.client.get(
                        f"{self.base_url}/tasks/{self.task_id}/status"
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        task_status = status_data.get("status", "").lower()
                        if task_status in ["failed", "error"]:
                            self.log_result(
                                "任务状态检查",
                                False,
                                f"任务创建后状态异常",
                                status_data,
                            )
                        else:
                            self.log_result(
                                "任务状态检查",
                                True,
                                f"任务状态: {task_status}",
                                status_data,
                            )
                    else:
                        self.log_result(
                            "任务状态检查",
                            False,
                            f"无法获取任务状态: HTTP {status_response.status_code}",
                            status_response.text,
                        )
                except Exception as status_check_error:
                    self.log_result(
                        "任务状态检查",
                        False,
                        f"状态检查异常: {str(status_check_error)}",
                        {"error": str(status_check_error)},
                    )
                return True
            else:
                self.log_result(
                    "创建视频任务",
                    False,
                    f"任务创建失败: {create_resp.status_code}",
                    create_resp.text,
                )
                return False

        except Exception as e:
            self.log_result("创建视频任务", False, f"任务创建异常: {str(e)}")
            return False

    async def test_monitor_task_progress(self) -> bool:
        """测试监控任务进度"""
        log_info("=" * 60)
        log_info("步骤 6: 监控任务执行进度")
        log_info("=" * 60)

        if not self.task_id:
            self.log_result("监控任务进度", False, "没有可监控的任务ID")
            return False

        max_wait_time = 1800  # 最大等待30分钟
        check_interval = 10  # 每10秒检查一次
        start_time = time.time()

        expected_stages = ["素材处理", "素材分析", "脚本生成", "视频生成"]

        completed_stages = set()
        # 阶段成果打印去重标记
        printed_materials = False
        printed_analysis = False
        printed_script = False
        last_status = None
        last_description = None
        last_stage = None

        try:
            while time.time() - start_time < max_wait_time:
                # 获取任务状态
                try:
                    response = await self.client.get(
                        f"{self.base_url}/tasks/{self.task_id}/status"
                    )

                    if response.status_code == 200:
                        try:
                            status_data = response.json()
                        except Exception:
                            self.log_result(
                                "获取任务状态",
                                False,
                                "状态返回非JSON",
                                {
                                    "response_text": (
                                        response.text[:1000] if response.text else ""
                                    )
                                },
                            )
                            await asyncio.sleep(check_interval)
                            continue
                        task_status = status_data.get("status", "").lower()
                        progress = status_data.get("progress", 0)
                        description = status_data.get("description", "")
                        current_stage = status_data.get("current_stage", "")
                        stage_message = status_data.get("stage_message", "")
                        celery_status = status_data.get("celery_status", "")
                        error_message = status_data.get("error_message", "")

                        # 只在状态、描述或阶段发生变化时打印
                        if (
                            task_status != last_status
                            or description != last_description
                            or current_stage != last_stage
                        ):
                            log_info(
                                f"⏱️  任务状态: {task_status}, 进度: {progress:.1f}%"
                            )
                            if celery_status:
                                log_info(f"   🧰 Celery: {celery_status}")
                            if current_stage:
                                log_info(f"   🔹 当前阶段: {current_stage}")
                            if stage_message:
                                log_info(f"   🔸 阶段说明: {stage_message}")
                            if description:
                                log_error(f"   📝 描述: {description}")
                            if error_message:
                                log_error(f"❌ 错误信息: {error_message}")

                            # 阶段成果：素材清单
                            if not printed_materials and (
                                current_stage == "素材处理"
                                or "素材处理" in (description or stage_message)
                            ):
                                media_count = status_data.get("media_items_count", 0)
                                if media_count > 0:
                                    try:
                                        media_resp = await self.client.get(
                                            f"{self.base_url}/tasks/{self.task_id}/media"
                                        )
                                        if media_resp.status_code == 200:
                                            media_items = media_resp.json()
                                            self._print_materials_list(media_items)
                                            printed_materials = True
                                    except Exception as _:
                                        pass

                            # 阶段成果：素材分析
                            if not printed_analysis and (
                                current_stage == "素材分析"
                                or "素材分析" in (description or stage_message)
                            ):
                                try:
                                    detail_resp = await self.client.get(
                                        f"{self.base_url}/tasks/{self.task_id}"
                                    )
                                    if detail_resp.status_code == 200:
                                        detail = detail_resp.json()
                                        analyses = detail.get("material_analyses", [])
                                        if analyses:
                                            self._print_analysis_summary(analyses)
                                            printed_analysis = True
                                except Exception as _:
                                    pass

                            # 阶段成果：脚本生成
                            if not printed_script and (
                                current_stage == "脚本生成"
                                or "脚本生成" in (description or stage_message)
                            ):
                                try:
                                    detail_resp = await self.client.get(
                                        f"{self.base_url}/tasks/{self.task_id}"
                                    )
                                    if detail_resp.status_code == 200:
                                        detail = detail_resp.json()
                                        script_content = detail.get("script_content")
                                        if (
                                            isinstance(script_content, dict)
                                            and script_content
                                        ):
                                            self._print_script_summary(script_content)
                                            printed_script = True
                                except Exception as _:
                                    pass

                            # 打印视频信息（支持多视频）
                            self._display_video_info(status_data, detailed=False)

                            last_status = task_status
                            last_description = description
                            last_stage = current_stage

                        # 检查是否完成了新的阶段（基于描述或阶段名）
                        for stage in expected_stages:
                            if (
                                (description and stage in description)
                                or (current_stage and stage in current_stage)
                            ) and stage not in completed_stages:
                                completed_stages.add(stage)
                                self.log_result(
                                    f"阶段完成-{stage}",
                                    True,
                                    f"阶段'{stage}'执行完成",
                                    {
                                        "progress": progress,
                                        "current_stage": current_stage,
                                        "stage_message": stage_message,
                                    },
                                )

                        # 检查任务是否完成或失败
                        if task_status in ["completed"]:
                            self.log_result(
                                "任务完成", True, "视频生成任务完全完成", status_data
                            )

                            # 获取任务详情
                            try:
                                detail_response = await self.client.get(
                                    f"{self.base_url}/tasks/{self.task_id}"
                                )

                                if detail_response.status_code == 200:
                                    task_detail = detail_response.json()

                                    log_info("\n" + "=" * 80)
                                    log_info("🎉 任务完成! 最终结果详情:")
                                    log_info("=" * 80)

                                    # 打印脚本详情（来自任务详情的 script_content）
                                    script_content = task_detail.get(
                                        "script_content", {}
                                    )
                                    if (
                                        isinstance(script_content, dict)
                                        and script_content
                                    ):
                                        self._print_script_summary(
                                            script_content, final=True
                                        )

                                    # 打印视频详情（支持多视频）
                                    self._display_video_info(task_detail, detailed=True)

                                    log_info("\n" + "=" * 80)

                                    self.log_result(
                                        "获取任务详情",
                                        True,
                                        "任务详情获取成功",
                                        task_detail,
                                    )
                            except Exception as detail_error:
                                self.log_result(
                                    "获取任务详情",
                                    False,
                                    f"获取任务详情失败: {str(detail_error)}",
                                )

                            return True

                        elif task_status in ["failed", "error"]:
                            error_details = {
                                "status": task_status,
                                "progress": progress,
                                "description": description,
                                "error_message": error_message,
                                "completed_stages": list(completed_stages),
                            }
                            self.log_result(
                                "任务失败",
                                False,
                                f"任务执行失败: {error_message or description}",
                                error_details,
                            )
                            return False

                        elif task_status == "cancelled":
                            self.log_result(
                                "任务取消",
                                False,
                                "任务被取消",
                                {
                                    "description": description,
                                    "completed_stages": list(completed_stages),
                                },
                            )
                            return False

                    else:
                        error_msg = f"获取任务状态失败: HTTP {response.status_code}"
                        log_error(f"❌ {error_msg}")
                        # 记录错误但不立即返回，给系统一些恢复时间
                        self.log_result(
                            "获取任务状态",
                            False,
                            error_msg,
                            {"response": response.text if response.text else ""},
                        )
                        # 等待一段时间后继续尝试
                        await asyncio.sleep(check_interval)
                        continue

                except Exception as status_error:
                    error_msg = f"获取任务状态异常: {str(status_error)}"
                    log_error(f"❌ {error_msg}")
                    self.log_result(
                        "获取任务状态", False, error_msg, {"error": str(status_error)}
                    )
                    # 等待一段时间后继续尝试
                    await asyncio.sleep(check_interval)
                    continue

                # 等待下次检查
                await asyncio.sleep(check_interval)

            # 超时
            timeout_details = {
                "last_status": last_status,
                "last_description": last_description,
                "completed_stages": list(completed_stages),
                "elapsed_time": time.time() - start_time,
            }
            self.log_result(
                "任务监控超时",
                False,
                f"任务在{max_wait_time}秒内未完成",
                timeout_details,
            )
            return False

        except Exception as e:
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "last_status": last_status,
                "last_description": last_description,
                "completed_stages": list(completed_stages),
            }
            self.log_result("监控任务进度", False, f"监控异常: {str(e)}", error_details)
            return False

    async def test_task_management(self) -> bool:
        """测试任务管理功能"""
        log_info("=" * 60)
        log_info("步骤 7: 任务管理功能测试")
        log_info("=" * 60)

        try:
            # 7.1 获取任务列表
            response = await self.client.get(f"{self.base_url}/tasks/")

            if response.status_code == 200:
                tasks = response.json()
                self.log_result(
                    "获取任务列表",
                    True,
                    f"获取成功，共{len(tasks)}个任务",
                    {"count": len(tasks)},
                )
            else:
                self.log_result(
                    "获取任务列表",
                    False,
                    f"获取失败: {response.status_code}",
                    response.text,
                )
                return False

            # 7.2 获取任务统计
            response = await self.client.get(f"{self.base_url}/tasks/stats")

            if response.status_code == 200:
                stats = response.json()
                self.log_result("获取任务统计", True, "统计信息获取成功", stats)
            else:
                self.log_result(
                    "获取任务统计",
                    False,
                    f"获取失败: {response.status_code}",
                    response.text,
                )

            # 7.3 获取任务媒体文件
            if self.task_id:
                response = await self.client.get(
                    f"{self.base_url}/tasks/{self.task_id}/media"
                )

                if response.status_code == 200:
                    media_items = response.json()
                    self.log_result(
                        "获取任务媒体",
                        True,
                        f"获取成功，共{len(media_items)}个媒体文件",
                        {"count": len(media_items)},
                    )
                else:
                    self.log_result(
                        "获取任务媒体",
                        False,
                        f"获取失败: {response.status_code}",
                        response.text,
                    )

            return True

        except Exception as e:
            self.log_result("任务管理功能", False, f"功能测试异常: {str(e)}")
            return False

    async def test_script_styles_comparison(self) -> bool:
        """测试脚本风格对比"""
        log_info("=" * 60)
        log_info("步骤 6: 脚本风格对比测试")
        log_info("=" * 60)

        styles_to_test = ["default", "product_geek"]
        comparison_results = {}

        for style in styles_to_test:
            log_info(f"\n🎭 测试风格: {style}")
            log_info("-" * 40)

            # 临时修改风格设置
            original_style = self.script_style
            self.script_style = style

            try:
                # 目录上传（按同一目录）
                dir_path = Path(self.local_dir)
                if not dir_path.exists() or not dir_path.is_dir():
                    self.log_result(
                        f"脚本风格对比-{style}", False, f"目录不存在: {self.local_dir}"
                    )
                    self.script_style = original_style
                    continue
                title = f"{dir_path.name}_风格_{style}"
                all_files = [p for p in dir_path.rglob("*") if p.is_file()]
                to_upload = all_files[:50]
                files = [
                    (
                        "files",
                        (
                            p.name,
                            open(p, "rb"),
                            (
                                mimetypes.guess_type(str(p))[0]
                                or "application/octet-stream"
                            ),
                        ),
                    )
                    for p in to_upload
                ]
                upload_resp = await self.client.post(
                    f"{self.base_url}/tasks/attachments/upload", files=files
                )
                for _, (_, fh, _) in files:
                    try:
                        fh.close()
                    except Exception:
                        pass
                if upload_resp.status_code != 200:
                    comparison_results[style] = {
                        "success": False,
                        "error": f"上传失败: HTTP {upload_resp.status_code}",
                    }
                    self.log_result(
                        f"脚本风格对比-{style}",
                        False,
                        f"上传失败: HTTP {upload_resp.status_code}",
                        upload_resp.text,
                    )
                    continue
                upload_data = upload_resp.json()
                items = upload_data.get("items", [])
                media_urls = [
                    it.get("url") for it in items if it.get("success") and it.get("url")
                ]
                files_form = [
                    ("title", (None, title)),
                    ("mode", (None, "multi_scene")),
                    ("script_style", (None, style)),
                    ("multi_video_count", (None, "3")),
                ] + [("media_urls", (None, u)) for u in media_urls]
                response = await self.client.post(
                    f"{self.base_url}/tasks/create-video-task", files=files_form
                )

                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data.get("id")

                    comparison_results[style] = {
                        "task_id": task_id,
                        "success": True,
                        "task_data": task_data,
                    }

                    self.log_result(
                        f"脚本风格对比-{style}",
                        True,
                        f"任务创建成功，ID: {task_id}",
                        {"style": style, "task_id": task_id},
                    )

                    # 等待一段时间让任务开始处理
                    await asyncio.sleep(2)

                else:
                    comparison_results[style] = {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                    }

                    self.log_result(
                        f"脚本风格对比-{style}",
                        False,
                        f"任务创建失败: {response.status_code}",
                        response.text,
                    )

            except Exception as e:
                comparison_results[style] = {"success": False, "error": str(e)}

                self.log_result(f"脚本风格对比-{style}", False, f"测试异常: {str(e)}")

                # 无临时文件需要清理（目录模式）

            finally:
                # 恢复原始风格设置
                self.script_style = original_style

        # 生成对比报告
        log_info("\n📊 脚本风格对比结果:")
        log_info("=" * 50)

        success_count = 0
        for style, result in comparison_results.items():
            if result.get("success", False):
                success_count += 1
                task_id = result.get("task_id", "未知")
                log_info(f"✅ {style:15} - 任务ID: {task_id}")
            else:
                error = result.get("error", "未知错误")
                log_error(f"❌ {style:15} - 错误: {error}")

        log_info(
            f"\n📈 成功率: {success_count}/{len(styles_to_test)} ({success_count/len(styles_to_test)*100:.1f}%)"
        )

        if success_count > 0:
            log_info("\n💡 提示: 您可以通过以下方式查看不同风格的任务:")
            log_info("   - 使用 GET /tasks/ 接口查看所有任务")
            log_info("   - 使用 GET /tasks/{task_id} 接口查看具体任务详情")
            log_info("   - 比较不同风格生成的脚本内容差异")

        # 如果至少有一个风格测试成功，就认为整体测试成功
        return success_count > 0

    def _display_video_info(self, data: Dict[str, Any], detailed: bool = False):
        """显示视频信息（多视频）"""
        multi_video_info = data.get("multi_video_info", {})

        # 显示多视频任务的总体信息
        total_videos = multi_video_info.get("total_videos", 0)
        completed_count = multi_video_info.get("completed_count", 0)
        failed_count = multi_video_info.get("failed_count", 0)
        processing_count = multi_video_info.get("processing_count", 0)

        log_info("\n🎬 多视频任务信息:")
        log_info(f"   📊 总视频数: {total_videos}")
        log_info(f"   ✅ 已完成: {completed_count}")
        log_info(f"   ⏳ 处理中: {processing_count}")
        log_error(f"   ❌ 失败: {failed_count}")

        # 显示已完成的视频
        completed_videos = multi_video_info.get("completed_videos", [])
        if completed_videos:
            log_info("\n✅ 已完成的视频:")
            for i, video in enumerate(completed_videos, 1):
                log_info(f"\n   视频 {i}/{len(completed_videos)}:")
                log_info(f"   🆔 子任务ID: {video.get('sub_task_id')}")
                log_info(f"   🎭 脚本风格: {video.get('script_style', '默认')}")
                if video.get("video_url"):
                    log_info(f"   🔗 视频URL: {video.get('video_url')}")
                if video.get("thumbnail_url"):
                    log_info(f"   🖼️  缩略图URL: {video.get('thumbnail_url')}")
                if video.get("video_duration"):
                    log_info(f"   ⏱️  时长: {video.get('video_duration')}秒")

        # 显示失败的视频（如果是详细模式或有失败的视频）
        failed_videos = multi_video_info.get("failed_videos", [])
        if failed_videos and (detailed or failed_count > 0):
            log_error("\n❌ 失败的视频:")
            for i, video in enumerate(failed_videos, 1):
                log_error(f"\n   视频 {i}/{len(failed_videos)}:")
                log_error(f"   🆔 子任务ID: {video.get('sub_task_id')}")
                log_error(f"   🎭 脚本风格: {video.get('script_style', '默认')}")
                log_error(f"   ❌ 错误信息: {video.get('error_message', '未知错误')}")

        # 显示处理中的视频（仅在详细模式下）
        processing_videos = multi_video_info.get("processing_videos", [])
        if processing_videos and detailed:
            log_info("\n⏳ 处理中的视频:")
            for i, video in enumerate(processing_videos, 1):
                log_info(f"\n   视频 {i}/{len(processing_videos)}:")
                log_info(f"   🆔 子任务ID: {video.get('sub_task_id')}")
                log_info(f"   🎭 脚本风格: {video.get('script_style', '默认')}")
                log_info(f"   📊 进度: {video.get('progress', 0)}%")

    def _print_materials_list(self, media_items: Any):
        try:
            items = media_items if isinstance(media_items, list) else []
            log_info("\n🧩 素材清单:")
            log_info(f"   共 {len(items)} 个素材，示例：")
            for item in items[:5]:
                name = item.get("filename") or os.path.basename(
                    item.get("local_path") or ""
                )
                log_info(f"   - [{item.get('media_type', 'unknown')}] {name}")
        except Exception:
            pass

    def _print_analysis_summary(self, analyses: Any):
        try:
            arr = analyses if isinstance(analyses, list) else []
            log_info("\n🧪 素材分析结果:")
            log_info(f"   共 {len(arr)} 条分析记录")
            for a in arr[:3]:
                summary = a.get("summary") or a.get("result") or ""
                media_ref = a.get("media_filename") or a.get("media_id")
                line = (
                    f"   - {media_ref}: {summary[:120]}"
                    if summary
                    else f"   - {media_ref}"
                )
                log_info(line)
        except Exception:
            pass

    def _print_script_summary(
        self, script_content: Dict[str, Any], final: bool = False
    ):
        title = script_content.get("title")
        description = script_content.get("description")
        narration = script_content.get("narration") or script_content.get("full_text")
        tags = script_content.get("tags") or []
        est = script_content.get("estimated_duration") or script_content.get("duration")
        wc = script_content.get("word_count")
        mc = script_content.get("material_count")
        log_info("\n📄 {}脚本信息:".format("最终" if final else ""))
        if title:
            log_info(f"   📝 标题: {title}")
        if description:
            log_info(f"   📄 描述: {description}")
        if est:
            log_info(f"   ⏱️  时长(估): {est}秒")
        if wc:
            log_info(f"   📊 字数: {wc}字")
        if mc:
            log_info(f"   🖼️  素材数: {mc}个")
        if tags:
            log_info(f"   🏷️  标签: {', '.join(tags)}")
        if narration:
            preview = (
                narration
                if final
                else (narration[:280] + ("…" if len(narration) > 280 else ""))
            )
            log_info(f"   🎙️  旁白预览:\n{preview}")

    def generate_test_report(self):
        """生成测试报告"""
        log_info("=" * 80)
        log_info("🎯 TextLoom 业务穿越测试报告")
        log_info("=" * 80)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests

        # 定义关键步骤
        critical_steps = {
            "API健康检查",
            "用户注册",
            "用户登录",
            "创建视频任务",
            "任务完成",
            "任务失败",
            "任务监控超时",
        }

        # 统计关键步骤失败
        critical_failures = [
            r
            for r in self.test_results
            if not r["success"] and r["step"] in critical_steps
        ]

        log_info(f"📊 测试统计:")
        log_info(f"   总测试数: {total_tests}")
        log_info(f"   通过数: {passed_tests}")
        log_info(f"   失败数: {failed_tests}")
        log_info(f"   关键步骤失败数: {len(critical_failures)}")
        if total_tests > 0:
            log_info(f"   成功率: {passed_tests/total_tests*100:.1f}%")
        log_info()

        if critical_failures:
            log_error("❌ 关键步骤失败:")
            for failure in critical_failures:
                log_error(f"   • {failure['step']}: {failure['message']}")
                if failure.get("data"):
                    data_obj = failure["data"]
                    if isinstance(data_obj, dict):
                        error_msg = data_obj.get("error_message", "")
                        description = data_obj.get("description", "")
                        if error_msg:
                            log_error(f"     错误信息: {error_msg}")
                        if description:
                            log_error(f"     详细描述: {description}")
                    else:
                        log_error(f"     错误数据: {str(data_obj)[:200]}")
            log_info()

        log_info("📝 详细结果:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            critical = "[关键步骤]" if result["step"] in critical_steps else ""
            log_info(f"   {status} {result['step']}{critical}: {result['message']}")
            if not result["success"] and result.get("data"):
                data_obj = result["data"]
                if isinstance(data_obj, dict):
                    error_msg = data_obj.get("error_message", "")
                    description = data_obj.get("description", "")
                    if error_msg:
                        log_error(f"     错误信息: {error_msg}")
                    if description:
                        log_error(f"     详细描述: {description}")
                else:
                    log_info(f"     原始数据: {str(data_obj)[:500]}")

        log_info()

        if failed_tests == 0:
            log_info("🎉 恭喜！所有测试都通过了！")
            log_info("🚀 TextLoom系统已准备好投入使用！")
        elif critical_failures:
            log_error("❌ 测试失败！关键步骤存在问题，系统无法正常工作！")
            log_error("💡 请优先修复关键步骤的问题")
        else:
            log_warning("⚠️  部分非关键步骤失败，但系统基本功能可用")
            log_info("💡 建议在系统投入使用前修复这些问题")

        # 保存详细报告到文件
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": {
                        "total_tests": total_tests,
                        "passed_tests": passed_tests,
                        "failed_tests": failed_tests,
                        "critical_failures": len(critical_failures),
                        "success_rate": (
                            passed_tests / total_tests * 100 if total_tests > 0 else 0
                        ),
                    },
                    "critical_failures": [
                        {
                            "step": f["step"],
                            "message": f["message"],
                            "data": f.get("data", {}),
                        }
                        for f in critical_failures
                    ],
                    "results": self.test_results,
                    "test_info": {
                        "persona_id": self.persona_id,
                        "task_id": self.task_id,
                        "base_url": self.base_url,
                        "video_mode": "multi_scene",
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        log_info(f"📄 详细报告已保存到: {report_file}")
        log_info("=" * 80)


async def main(
    base_url: str = BASE_URL,
    script_style: str = "default",
    test_styles_comparison: bool = False,
    local_dir: Optional[str] = None,
    desc_json: Optional[str] = None,
):
    """主测试函数"""
    log_info("🚀 启动 TextLoom 业务穿越测试")
    log_info(f"📍 测试服务地址: {base_url}")
    log_info(f"📝 脚本生成风格: {script_style}")

    if local_dir:
        log_info(f"📁 本地目录: {local_dir}")

    log_info(f"⏰ 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_info()

    async with BusinessTestRunner(
        base_url, script_style, local_dir, desc_json
    ) as runner:
        # 执行测试步骤
        steps = [
            ("API健康检查", runner.test_api_health, True),
            ("人设管理", runner.test_persona_management, False),
            ("创建视频任务", runner.test_create_video_task, True),
            ("监控任务进度", runner.test_monitor_task_progress, True),
            ("任务管理功能", runner.test_task_management, False),
        ]

        # 根据参数决定是否包含脚本风格对比测试
        if test_styles_comparison:
            steps.append(
                ("脚本风格对比测试", runner.test_script_styles_comparison, False)
            )

        for step_name, step_func, is_critical in steps:
            log_info(f"🔄 开始执行: {step_name}")
            try:
                success = await step_func()
                if not success:
                    log_warning(f"⚠️  {step_name} 失败")
                    if is_critical:
                        log_error(f"❌ {step_name}是关键步骤，测试终止")
                        break
                    else:
                        log_warning(f"⚠️  继续执行其他测试...")
            except Exception as e:
                runner.log_result(step_name, False, f"步骤执行异常: {str(e)}")
                log_error(f"❌ {step_name} 执行异常: {e}")
                if is_critical:
                    log_error(f"❌ {step_name}是关键步骤，测试终止")
                    break

            log_info()

        # 生成测试报告
        runner.generate_test_report()


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="TextLoom 业务穿越测试脚本")
    parser.add_argument(
        "--local-dir",
        type=str,
        required=True,
        help="指定本地目录，批量上传目录内所有文件后创建任务（最多50个文件）",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=BASE_URL,
        help=f"API服务地址（默认：{BASE_URL}）",
    )

    parser.add_argument(
        "--script-style",
        type=str,
        choices=["default", "product_geek"],
        default="default",
        help="脚本生成风格：default（默认风格）或 product_geek（产品极客风格，默认）",
    )
    parser.add_argument(
        "--test-styles-comparison",
        action="store_true",
        help="启用脚本风格对比测试（会创建多个任务测试不同风格）",
    )
    parser.add_argument(
        "--desc-json",
        type=str,
        required=False,
        help='可选：JSON文件，提供一对一视频描述。支持两种格式：{"filename.mp4":"描述"} 或 [{"filename":"xxx.mp4","description":"..."}]',
    )

    args = parser.parse_args()

    # 设置配置
    test_base_url = args.base_url
    test_script_style = args.script_style
    test_styles_comparison = args.test_styles_comparison
    test_local_dir = args.local_dir

    log_info(f"📁 使用本地目录: {test_local_dir}")

    if args.base_url != BASE_URL:
        log_info(f"📍 使用指定的API地址: {test_base_url}")

    if args.script_style != "default":
        log_info(f"📝 使用指定的脚本生成风格: {test_script_style}")

    if args.test_styles_comparison:
        log_info("🔬 启用脚本风格对比测试")

    try:
        asyncio.run(
            main(
                test_base_url,
                test_script_style,
                test_styles_comparison,
                test_local_dir,
                args.desc_json,
            )
        )
    except KeyboardInterrupt:
        log_info("\n⏹️  测试被用户中断")
    except Exception as e:
        log_error(f"\n💥 测试执行异常: {e}")
        sys.exit(1)
