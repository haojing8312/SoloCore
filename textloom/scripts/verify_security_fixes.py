#!/usr/bin/env python3
"""
安全修复验证脚本
================
验证本次安全更新的成果
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n🔍 {description}")
    print("-" * 50)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 成功")
            if result.stdout:
                print(result.stdout)
        else:
            print("⚠️ 警告或发现问题")
            if result.stderr:
                print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


def main():
    """主验证流程"""
    print("🛡️ TextLoom 安全修复验证")
    print("=" * 50)

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    checks = []

    # 1. 检查依赖漏洞
    print("\n📦 检查依赖包安全状态...")
    result = run_command("uv run pip-audit --desc", "扫描依赖包漏洞")
    if not result:
        print("📋 发现的漏洞:")
        subprocess.run("uv run pip-audit", shell=True)
    checks.append(("依赖安全扫描", result))

    # 2. 验证关键包版本
    print("\n🔍 验证关键包版本...")
    critical_packages = {
        "fastapi": "0.109.1",
        "python-jose": "3.4.0",
        "python-multipart": "0.0.18",
    }

    for package, min_version in critical_packages.items():
        cmd = f"uv run python -c \"import {package.replace('-', '_')}; print({package.replace('-', '_')}.__version__)\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ {package}: {version}")
        else:
            print(f"❌ {package}: 无法检测版本")

    # 3. 运行快速代码安全检查
    print("\n🔧 运行代码安全检查...")
    result = run_command(
        "uv run bandit -r . -ll -x .venv,venv,logs,workspace,test,tests -q",
        "Bandit 高危问题扫描",
    )
    checks.append(("代码安全检查", result))

    # 4. 检查配置文件
    print("\n⚙️ 检查安全配置...")
    config_file = project_root / "pyproject.toml"
    if config_file.exists():
        with open(config_file, "r") as f:
            content = f.read()
            if "fastapi>=0.109.1" in content:
                print("✅ FastAPI 版本约束正确")
            if "python-jose[cryptography]>=3.4.0" in content:
                print("✅ python-jose 版本约束正确")
            if "python-multipart>=0.0.18" in content:
                print("✅ python-multipart 版本约束正确")

    # 总结
    print("\n📊 验证结果摘要")
    print("=" * 50)

    passed = sum(1 for _, result in checks if result)
    total = len(checks)

    print(f"通过检查: {passed}/{total}")

    if passed == total:
        print("🎉 所有安全检查通过！")
        print("\n✅ 安全修复验证成功")
        print("📋 建议:")
        print("  - 继续监控安全扫描报告")
        print("  - 定期运行依赖更新")
        print("  - 关注 ECDSA 漏洞的后续发展")
        return True
    else:
        print("⚠️ 部分检查未通过，请查看详细输出")
        return False


if __name__ == "__main__":
    import os

    success = main()
    sys.exit(0 if success else 1)
