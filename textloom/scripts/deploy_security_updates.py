#!/usr/bin/env python3
"""
安全更新部署脚本

这个脚本用于部署和配置TextLoom的安全更新，包括：
1. 创建必要的目录结构
2. 设置文件权限
3. 初始化安全配置
4. 运行安全测试
5. 验证部署结果

使用方法：
python scripts/deploy_security_updates.py --environment production
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SecurityDeployment:
    """安全更新部署器"""

    def __init__(self, environment: str = "production"):
        """
        初始化部署器

        Args:
            environment: 部署环境 (development, staging, production)
        """
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.security_dirs = {
            "quarantine": "./quarantine",
            "secure_uploads": "./secure_uploads",
            "audit_logs": "./logs",
            "temp_upload": "./secure_uploads/temp",
            "validated_files": "./secure_uploads/validated",
        }

    def deploy(self) -> bool:
        """
        执行完整的安全部署流程

        Returns:
            bool: 部署是否成功
        """
        try:
            logger.info(f"开始部署安全更新到 {self.environment} 环境")

            # 1. 检查系统要求
            if not self._check_system_requirements():
                return False

            # 2. 安装依赖
            if not self._install_dependencies():
                return False

            # 3. 创建目录结构
            if not self._create_directory_structure():
                return False

            # 4. 设置权限
            if not self._set_permissions():
                return False

            # 5. 初始化配置
            if not self._initialize_configuration():
                return False

            # 6. 运行测试
            if not self._run_security_tests():
                return False

            # 7. 验证部署
            if not self._verify_deployment():
                return False

            logger.info("✅ 安全更新部署成功！")
            self._print_deployment_summary()
            return True

        except Exception as e:
            logger.error(f"❌ 部署失败: {e}")
            return False

    def _check_system_requirements(self) -> bool:
        """检查系统要求"""
        logger.info("检查系统要求...")

        # 检查Python版本
        if sys.version_info < (3, 8):
            logger.error("需要Python 3.8或更高版本")
            return False

        # 检查必要的系统工具
        required_tools = ["git"]
        for tool in required_tools:
            if shutil.which(tool) is None:
                logger.error(f"缺少必要工具: {tool}")
                return False

        # 检查可选工具
        optional_tools = {"ffmpeg": "视频处理功能", "clamscan": "病毒扫描功能"}

        for tool, purpose in optional_tools.items():
            if shutil.which(tool) is None:
                logger.warning(f"可选工具 {tool} 未安装，{purpose}可能受限")

        logger.info("✅ 系统要求检查通过")
        return True

    def _install_dependencies(self) -> bool:
        """安装安全依赖"""
        logger.info("安装安全依赖包...")

        try:
            # 安装安全相关依赖
            security_requirements = self.project_root / "requirements-security.txt"
            if security_requirements.exists():
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(security_requirements),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("✅ 安全依赖安装完成")
            else:
                logger.warning("⚠️  安全依赖文件不存在，跳过安装")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 依赖安装失败: {e.stderr}")
            return False

    def _create_directory_structure(self) -> bool:
        """创建安全目录结构"""
        logger.info("创建安全目录结构...")

        try:
            for name, path in self.security_dirs.items():
                dir_path = Path(path)
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"  创建目录: {path}")

            # 创建子目录
            subdirs = [
                "secure_uploads/validated/2024",
                "secure_uploads/temp",
                "logs/security",
                "quarantine/info",
            ]

            for subdir in subdirs:
                Path(subdir).mkdir(parents=True, exist_ok=True)
                logger.info(f"  创建子目录: {subdir}")

            logger.info("✅ 目录结构创建完成")
            return True

        except Exception as e:
            logger.error(f"❌ 目录创建失败: {e}")
            return False

    def _set_permissions(self) -> bool:
        """设置文件和目录权限"""
        logger.info("设置安全权限...")

        try:
            # 设置敏感目录权限
            sensitive_dirs = ["quarantine", "secure_uploads", "logs"]

            for dir_name in sensitive_dirs:
                if os.path.exists(dir_name):
                    try:
                        os.chmod(dir_name, 0o700)  # 仅所有者可访问
                        logger.info(f"  设置权限: {dir_name} -> 700")
                    except OSError as e:
                        logger.warning(f"  权限设置失败: {dir_name} - {e}")

            # 设置配置文件权限
            config_files = [".env", "config.py"]

            for config_file in config_files:
                if os.path.exists(config_file):
                    try:
                        os.chmod(config_file, 0o600)  # 仅所有者可读写
                        logger.info(f"  设置权限: {config_file} -> 600")
                    except OSError as e:
                        logger.warning(f"  权限设置失败: {config_file} - {e}")

            logger.info("✅ 权限设置完成")
            return True

        except Exception as e:
            logger.error(f"❌ 权限设置失败: {e}")
            return False

    def _initialize_configuration(self) -> bool:
        """初始化安全配置"""
        logger.info("初始化安全配置...")

        try:
            # 创建安全配置文件
            security_config = {
                "environment": self.environment,
                "security_enabled": True,
                "file_validation": {
                    "max_file_size": 52428800,  # 50MB
                    "allowed_extensions": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".mp4",
                        ".mov",
                        ".md",
                        ".txt",
                    ],
                    "enable_virus_scan": False,
                    "enable_content_scan": True,
                },
                "url_validation": {
                    "allow_private_ips": False,
                    "max_urls_per_request": 50,
                    "timeout_seconds": 30,
                },
                "rate_limiting": {
                    "requests_per_minute": (
                        100 if self.environment != "production" else 60
                    ),
                    "burst_limit": 20 if self.environment != "production" else 10,
                },
                "audit_logging": {
                    "enabled": True,
                    "log_file": "./logs/security/audit.log",
                    "log_sensitive_data": self.environment == "development",
                },
            }

            # 写入配置文件
            config_file = Path("security_config.json")
            with open(config_file, "w") as f:
                json.dump(security_config, f, indent=2)

            # 设置配置文件权限
            os.chmod(config_file, 0o600)

            logger.info("✅ 安全配置初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 配置初始化失败: {e}")
            return False

    def _run_security_tests(self) -> bool:
        """运行安全测试"""
        logger.info("运行安全测试...")

        try:
            # 检查测试文件是否存在
            test_file = (
                self.project_root / "tests" / "security" / "test_security_validators.py"
            )
            if not test_file.exists():
                logger.warning("⚠️  安全测试文件不存在，跳过测试")
                return True

            # 运行安全测试
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("✅ 安全测试通过")
                return True
            else:
                logger.error(f"❌ 安全测试失败:\n{result.stdout}\n{result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ 测试执行失败: {e}")
            return False

    def _verify_deployment(self) -> bool:
        """验证部署结果"""
        logger.info("验证部署结果...")

        try:
            # 验证目录结构
            for name, path in self.security_dirs.items():
                if not Path(path).exists():
                    logger.error(f"❌ 目录不存在: {path}")
                    return False

            # 验证Python模块导入
            security_modules = [
                "utils.security.file_validator",
                "utils.security.input_validator",
                "utils.security.secure_file_handler",
                "utils.security.security_middleware",
            ]

            for module in security_modules:
                try:
                    __import__(module)
                    logger.info(f"  ✅ 模块导入成功: {module}")
                except ImportError as e:
                    logger.error(f"  ❌ 模块导入失败: {module} - {e}")
                    return False

            logger.info("✅ 部署验证通过")
            return True

        except Exception as e:
            logger.error(f"❌ 部署验证失败: {e}")
            return False

    def _print_deployment_summary(self):
        """打印部署摘要"""
        summary = f"""
🔒 TextLoom 安全更新部署完成

环境: {self.environment}
时间: {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}

已部署的安全特性:
✅ 文件上传安全验证
✅ URL安全验证和SSRF防护
✅ 输入验证和注入攻击防护
✅ 安全中间件和速率限制
✅ 安全审计日志
✅ 恶意内容检测

目录结构:
{chr(10).join(f'  📁 {path}' for path in self.security_dirs.values())}

下一步:
1. 更新应用程序以使用新的安全路由
2. 配置环境变量（参考 .env.example）
3. 启用安全中间件
4. 监控安全日志

文档:
📖 详细使用指南: docs/SECURITY_IMPLEMENTATION_GUIDE.md
🧪 测试安全功能: pytest tests/security/
📊 监控安全日志: logs/security/audit.log
"""
        print(summary)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="部署TextLoom安全更新")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="production",
        help="部署环境",
    )
    parser.add_argument("--skip-tests", action="store_true", help="跳过安全测试")
    parser.add_argument("--force", action="store_true", help="强制部署，忽略警告")

    args = parser.parse_args()

    # 创建部署器并执行部署
    deployer = SecurityDeployment(args.environment)

    if args.skip_tests:
        deployer._run_security_tests = lambda: True

    success = deployer.deploy()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
