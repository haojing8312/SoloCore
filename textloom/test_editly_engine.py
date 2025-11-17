#!/usr/bin/env python3
"""
Editly 视频引擎测试脚本

用法:
    python test_editly_engine.py

功能:
    - 测试基础视频合成
    - 验证配置转换
    - 检查输出质量

作者: Claude
创建: 2025-11-17
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from services.editly_video_engine import EditlyVideoEngine


def test_basic_video_generation():
    """测试基础视频生成"""
    print("=" * 60)
    print("测试：基础视频生成")
    print("=" * 60)

    # 准备测试数据
    script_data = {
        "title": "测试视频标题",
        "subtitle": "Editly 引擎测试",
        "scenes": [
            {
                "scene_id": 1,
                "narration": "这是第一个场景的旁白文本",
                "material_id": "mat_001",
                "duration": 5.0,
            },
            {
                "scene_id": 2,
                "narration": "这是第二个场景的旁白文本",
                "material_id": "mat_002",
                "duration": 4.0,
            },
            {
                "scene_id": 3,
                "narration": "这是第三个场景，总结全文",
                "material_id": None,  # 无素材，仅背景+字幕
                "duration": 3.0,
            },
        ],
    }

    # 准备媒体文件（需要实际存在的文件）
    media_files = [
        {
            "id": "mat_001",
            "file_url": "workspace/materials/images/sample1.jpg",
            "filename": "sample1.jpg",
        },
        {
            "id": "mat_002",
            "file_url": "workspace/materials/images/sample2.jpg",
            "filename": "sample2.jpg",
        },
    ]

    # 输出路径
    output_path = "workspace/output/test_editly_output.mp4"

    # 创建输出目录
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 执行生成
    engine = EditlyVideoEngine()

    def progress_callback(progress: int):
        print(f"进度: {progress}%")

    result = engine.generate_video(
        script_data=script_data,
        media_files=media_files,
        output_path=output_path,
        progress_callback=progress_callback,
    )

    # 验证结果
    print("\n" + "=" * 60)
    print("测试结果:")
    print("=" * 60)
    if result["success"]:
        print(f"✅ 视频生成成功!")
        print(f"   输出路径: {result['video_path']}")
        print(f"   视频时长: {result['duration']}s")
        print(f"   合成引擎: {result['engine']}")
    else:
        print(f"❌ 视频生成失败!")
        print(f"   错误信息: {result.get('error')}")

    return result


def test_config_conversion():
    """测试配置转换"""
    print("=" * 60)
    print("测试：配置转换")
    print("=" * 60)

    engine = EditlyVideoEngine()

    script_data = {
        "scenes": [
            {
                "scene_id": 1,
                "narration": "测试场景",
                "material_id": "mat_001",
                "duration": 5.0,
            }
        ]
    }

    media_files = [
        {
            "id": "mat_001",
            "file_url": "test.jpg",
            "filename": "test.jpg",
        }
    ]

    config = engine._convert_to_editly_config(
        script_data, media_files, "output.mp4"
    )

    print(f"生成的配置:")
    import json
    print(json.dumps(config, indent=2, ensure_ascii=False))

    # 验证配置结构
    assert "outPath" in config
    assert "clips" in config
    assert len(config["clips"]) == 1
    assert len(config["clips"][0]["layers"]) > 0

    print("✅ 配置转换测试通过")


def main():
    """主函数"""
    print("\n" + "🎬" * 30)
    print("Editly 视频引擎测试套件")
    print("🎬" * 30 + "\n")

    try:
        # 测试 1：配置转换
        test_config_conversion()
        print("\n")

        # 测试 2：基础视频生成（需要实际素材文件）
        # 注意：这需要你准备一些测试图片/视频
        print("⚠️ 跳过视频生成测试（需要准备测试素材）")
        print("   准备测试素材后，取消注释下面这行:")
        print("   # test_basic_video_generation()")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "✅" * 30)
    print("所有测试完成")
    print("✅" * 30 + "\n")


if __name__ == "__main__":
    main()
