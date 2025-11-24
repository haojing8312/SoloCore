#!/usr/bin/env python3
"""
TextLoom 备份系统集成安装脚本
============================

自动化安装和配置完整的备份和灾难恢复系统
与现有TextLoom配置系统无缝集成

Usage:
    python scripts/setup_backup_system.py install
    python scripts/setup_backup_system.py configure
    python scripts/setup_backup_system.py validate
    python scripts/setup_backup_system.py uninstall
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

import logging

from config import Settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class BackupSystemInstaller:
    """备份系统安装器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.settings = Settings()

        # 安装路径
        self.scripts_dir = self.project_root / "scripts"
        self.docker_dir = self.project_root / "docker"
        self.backup_dir = self.project_root / "backups"
        self.logs_dir = self.project_root / "logs"

        # 配置文件
        self.env_backup_file = self.project_root / ".env.backup"
        self.env_backup_example = self.project_root / ".env.backup.example"

        # Docker相关文件
        self.docker_compose_backup = self.project_root / "docker-compose.backup.yml"

    def install(self) -> bool:
        """安装备份系统"""
        logger.info("开始安装TextLoom备份和灾难恢复系统")

        try:
            # 1. 创建必要的目录
            self._create_directories()

            # 2. 检查依赖
            self._check_dependencies()

            # 3. 生成配置文件
            self._generate_config()

            # 4. 设置权限
            self._setup_permissions()

            # 5. 验证安装
            if self._validate_installation():
                logger.info("备份系统安装成功！")
                self._print_next_steps()
                return True
            else:
                logger.error("备份系统安装验证失败")
                return False

        except Exception as e:
            logger.error(f"安装过程中出现错误: {e}")
            return False

    def _create_directories(self):
        """创建必要的目录"""
        logger.info("创建目录结构")

        directories = [
            self.backup_dir,
            self.backup_dir / "local",
            self.backup_dir / "config",
            self.logs_dir,
            self.project_root / "minio_data",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {directory}")

    def _check_dependencies(self):
        """检查系统依赖"""
        logger.info("检查系统依赖")

        # 检查Python依赖
        required_packages = [
            "asyncpg",
            "redis",
            "psutil",
            "cryptography",
            "aiohttp",
            "aiofiles",
            "minio",
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logger.warning(f"缺少Python包: {', '.join(missing_packages)}")
            logger.info("尝试安装缺少的包...")

            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + missing_packages, check=True
            )

        # 检查系统工具
        system_tools = ["pg_dump", "pg_restore", "redis-cli", "curl", "nc"]
        missing_tools = []

        for tool in system_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)

        if missing_tools:
            logger.warning(f"缺少系统工具: {', '.join(missing_tools)}")
            logger.info("请根据您的操作系统安装这些工具")

    def _generate_config(self):
        """生成配置文件"""
        logger.info("生成备份系统配置")

        # 如果配置文件不存在，从示例文件复制
        if not self.env_backup_file.exists():
            if self.env_backup_example.exists():
                shutil.copy2(self.env_backup_example, self.env_backup_file)
                logger.info(f"创建配置文件: {self.env_backup_file}")
            else:
                logger.warning("示例配置文件不存在")

        # 更新配置文件，集成现有设置
        self._integrate_existing_config()

    def _integrate_existing_config(self):
        """集成现有配置"""
        logger.info("集成现有TextLoom配置")

        # 读取现有配置
        config_updates = {}

        # 数据库配置
        if self.settings.database_url:
            config_updates["DATABASE_URL"] = self.settings.database_url

        # Redis配置
        if self.settings.redis_host:
            config_updates["REDIS_HOST"] = self.settings.redis_host
        if self.settings.redis_port:
            config_updates["REDIS_PORT"] = str(self.settings.redis_port)
        if self.settings.redis_password:
            config_updates["REDIS_PASSWORD"] = self.settings.redis_password
        if self.settings.redis_db:
            config_updates["REDIS_DB"] = str(self.settings.redis_db)

        # 存储配置
        if self.settings.storage_type:
            config_updates["STORAGE_TYPE"] = self.settings.storage_type

        if self.settings.minio_endpoint:
            config_updates["MINIO_ENDPOINT"] = self.settings.minio_endpoint
        if self.settings.minio_access_key:
            config_updates["MINIO_ACCESS_KEY"] = self.settings.minio_access_key
        if self.settings.minio_secret_key:
            config_updates["MINIO_SECRET_KEY"] = self.settings.minio_secret_key
        if self.settings.minio_bucket:
            config_updates["MINIO_BUCKET"] = self.settings.minio_bucket

        if self.settings.obs_access_key:
            config_updates["OBS_ACCESS_KEY"] = self.settings.obs_access_key
        if self.settings.obs_secret_key:
            config_updates["OBS_SECRET_KEY"] = self.settings.obs_secret_key
        if self.settings.obs_endpoint:
            config_updates["OBS_ENDPOINT"] = self.settings.obs_endpoint
        if self.settings.obs_bucket:
            config_updates["OBS_BUCKET"] = self.settings.obs_bucket

        # 工作空间配置
        if self.settings.workspace_dir:
            config_updates["WORKSPACE_DIR"] = self.settings.workspace_dir

        # 更新配置文件
        if config_updates:
            self._update_env_file(config_updates)

    def _update_env_file(self, updates: Dict[str, str]):
        """更新环境变量文件"""
        if not self.env_backup_file.exists():
            return

        # 读取现有内容
        with open(self.env_backup_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 更新变量
        updated_lines = []
        updated_vars = set()

        for line in lines:
            line = line.rstrip()
            if "=" in line and not line.startswith("#"):
                var_name = line.split("=")[0].strip()
                if var_name in updates:
                    updated_lines.append(f"{var_name}={updates[var_name]}\n")
                    updated_vars.add(var_name)
                else:
                    updated_lines.append(line + "\n")
            else:
                updated_lines.append(line + "\n")

        # 添加新变量
        for var_name, value in updates.items():
            if var_name not in updated_vars:
                updated_lines.append(f"{var_name}={value}\n")

        # 写回文件
        with open(self.env_backup_file, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)

        logger.info(f"更新了 {len(updates)} 个配置项到 {self.env_backup_file}")

    def _setup_permissions(self):
        """设置文件权限"""
        logger.info("设置文件权限")

        # 设置脚本可执行权限
        script_files = [
            self.scripts_dir / "backup_manager.py",
            self.scripts_dir / "backup_monitor.py",
            self.scripts_dir / "disaster_recovery.py",
            self.scripts_dir / "backup_scheduler.sh",
            self.docker_dir / "backup-entrypoint.sh",
            self.docker_dir / "backup-healthcheck.sh",
        ]

        for script_file in script_files:
            if script_file.exists():
                script_file.chmod(0o755)
                logger.info(f"设置可执行权限: {script_file}")

        # 设置配置文件权限
        if self.env_backup_file.exists():
            self.env_backup_file.chmod(0o600)  # 仅所有者可读写
            logger.info(f"设置配置文件权限: {self.env_backup_file}")

    def _validate_installation(self) -> bool:
        """验证安装"""
        logger.info("验证备份系统安装")

        # 检查关键文件
        required_files = [
            self.scripts_dir / "backup_manager.py",
            self.scripts_dir / "backup_monitor.py",
            self.scripts_dir / "disaster_recovery.py",
            self.docker_compose_backup,
        ]

        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))

        if missing_files:
            logger.error(f"缺少关键文件: {', '.join(missing_files)}")
            return False

        # 检查目录
        required_dirs = [self.backup_dir, self.logs_dir]
        for dir_path in required_dirs:
            if not dir_path.exists():
                logger.error(f"缺少目录: {dir_path}")
                return False

        # 尝试导入备份模块
        try:
            from scripts.backup_manager import BackupManager
            from scripts.backup_monitor import BackupMonitor
            from scripts.disaster_recovery import DisasterRecoveryManager

            logger.info("Python模块导入正常")
        except ImportError as e:
            logger.error(f"模块导入失败: {e}")
            return False

        return True

    def _print_next_steps(self):
        """打印后续步骤"""
        print("\n" + "=" * 60)
        print("🎉 TextLoom备份系统安装成功！")
        print("=" * 60)
        print("\n📋 后续步骤:")
        print("\n1. 配置环境变量:")
        print(f"   编辑文件: {self.env_backup_file}")
        print("   设置数据库连接、存储后端和告警通知配置")

        print("\n2. 启动备份服务:")
        print("   # 使用Docker (推荐)")
        print("   docker-compose -f docker-compose.backup.yml up -d")
        print("   ")
        print("   # 或使用本地安装")
        print("   bash scripts/backup_scheduler.sh install")

        print("\n3. 验证系统运行:")
        print("   # 检查服务状态")
        print("   curl http://localhost:8081/api/status")
        print("   ")
        print("   # 运行测试备份")
        print("   python scripts/backup_manager.py backup --type daily")

        print("\n4. 访问监控界面:")
        print("   http://localhost:8081")

        print("\n📖 详细文档:")
        print("   查看 BACKUP_DISASTER_RECOVERY_GUIDE.md")

        print("\n⚠️  重要提醒:")
        print("   - 请妥善保管加密密钥")
        print("   - 定期测试恢复流程")
        print("   - 配置合适的告警通知")
        print("   - 监控磁盘空间使用")
        print("\n" + "=" * 60 + "\n")

    def configure(self) -> bool:
        """交互式配置"""
        logger.info("开始交互式配置")

        print("TextLoom备份系统配置向导")
        print("=" * 40)

        config = {}

        # 基础配置
        print("\n📂 基础配置")
        config["BACKUP_DAILY_RETENTION_DAYS"] = input("日备份保留天数 [7]: ") or "7"
        config["BACKUP_WEEKLY_RETENTION_WEEKS"] = input("周备份保留周数 [4]: ") or "4"
        config["BACKUP_MONTHLY_RETENTION_MONTHS"] = (
            input("月备份保留月数 [12]: ") or "12"
        )

        # 存储配置
        print("\n💾 存储配置")
        storage_type = input("存储类型 (local/minio/obs) [local]: ").lower() or "local"
        config["STORAGE_TYPE"] = storage_type

        if storage_type == "minio":
            config["MINIO_ENDPOINT"] = (
                input("MinIO端点 [localhost:9000]: ") or "localhost:9000"
            )
            config["MINIO_ACCESS_KEY"] = (
                input("MinIO访问密钥 [minioadmin]: ") or "minioadmin"
            )
            config["MINIO_SECRET_KEY"] = (
                input("MinIO秘密密钥 [minioadmin123]: ") or "minioadmin123"
            )
            config["MINIO_BUCKET"] = (
                input("MinIO存储桶 [textloom-backups]: ") or "textloom-backups"
            )

        elif storage_type == "obs":
            config["OBS_ACCESS_KEY"] = input("华为云OBS访问密钥: ")
            config["OBS_SECRET_KEY"] = input("华为云OBS秘密密钥: ")
            config["OBS_ENDPOINT"] = input("华为云OBS端点: ")
            config["OBS_BUCKET"] = input("华为云OBS存储桶: ")

        # 告警配置
        print("\n🚨 告警配置")
        email_alerts = input("启用邮件告警? (y/n) [n]: ").lower() == "y"
        config["BACKUP_EMAIL_ALERTS_ENABLED"] = str(email_alerts).lower()

        if email_alerts:
            config["BACKUP_SMTP_SERVER"] = input("SMTP服务器: ")
            config["BACKUP_SMTP_PORT"] = input("SMTP端口 [587]: ") or "587"
            config["BACKUP_SMTP_USERNAME"] = input("SMTP用户名: ")
            config["BACKUP_SMTP_PASSWORD"] = input("SMTP密码: ")
            config["BACKUP_EMAIL_FROM"] = input("发件人邮箱: ")
            config["BACKUP_EMAIL_TO"] = input("收件人邮箱: ")

        slack_alerts = input("启用Slack告警? (y/n) [n]: ").lower() == "y"
        config["BACKUP_SLACK_ALERTS_ENABLED"] = str(slack_alerts).lower()

        if slack_alerts:
            config["BACKUP_SLACK_WEBHOOK_URL"] = input("Slack Webhook URL: ")
            config["BACKUP_SLACK_CHANNEL"] = input("Slack频道 [#alerts]: ") or "#alerts"

        # 更新配置文件
        self._update_env_file(config)

        print(f"\n✅ 配置已保存到 {self.env_backup_file}")
        print("💡 提示: 您可以随时编辑该文件来修改配置")

        return True

    def validate(self) -> bool:
        """验证系统配置和状态"""
        logger.info("验证备份系统")

        print("TextLoom备份系统验证")
        print("=" * 30)

        validation_results = []

        # 1. 文件检查
        print("\n🔍 检查关键文件...")
        file_check = self._validate_installation()
        validation_results.append(("关键文件", file_check))
        print("✅ 通过" if file_check else "❌ 失败")

        # 2. 配置检查
        print("\n⚙️  检查配置文件...")
        config_check = self.env_backup_file.exists()
        validation_results.append(("配置文件", config_check))
        print("✅ 通过" if config_check else "❌ 失败")

        # 3. 依赖检查
        print("\n📦 检查Python依赖...")
        try:
            from scripts.backup_manager import BackupManager
            from scripts.backup_monitor import BackupMonitor

            deps_check = True
        except ImportError:
            deps_check = False

        validation_results.append(("Python依赖", deps_check))
        print("✅ 通过" if deps_check else "❌ 失败")

        # 4. 数据库连接检查
        print("\n🗄️  检查数据库连接...")
        try:
            if self.settings.database_url:
                import asyncio

                import asyncpg

                async def test_db():
                    conn = await asyncpg.connect(self.settings.database_url)
                    await conn.fetchrow("SELECT 1")
                    await conn.close()
                    return True

                db_check = asyncio.run(test_db())
            else:
                db_check = False
        except Exception:
            db_check = False

        validation_results.append(("数据库连接", db_check))
        print("✅ 通过" if db_check else "❌ 失败")

        # 5. Redis连接检查
        print("\n🔴 检查Redis连接...")
        try:
            if self.settings.redis_host:
                import redis

                client = redis.Redis(
                    host=self.settings.redis_host,
                    port=self.settings.redis_port or 6379,
                    password=self.settings.redis_password,
                )
                redis_check = client.ping()
            else:
                redis_check = False
        except Exception:
            redis_check = False

        validation_results.append(("Redis连接", redis_check))
        print("✅ 通过" if redis_check else "❌ 失败")

        # 6. 磁盘空间检查
        print("\n💾 检查磁盘空间...")
        import shutil

        free_space = shutil.disk_usage(self.backup_dir).free
        space_check = free_space > 5 * 1024**3  # 至少5GB
        validation_results.append(("磁盘空间", space_check))
        print(
            f"✅ 通过 ({free_space // (1024**3)}GB可用)" if space_check else "❌ 不足"
        )

        # 总结
        print("\n" + "=" * 50)
        passed = sum(1 for _, result in validation_results if result)
        total = len(validation_results)

        if passed == total:
            print(f"🎉 验证完成: {passed}/{total} 项通过")
            print("备份系统已准备就绪！")
            return True
        else:
            print(f"⚠️  验证完成: {passed}/{total} 项通过")
            print("请解决上述问题后重新验证")
            return False

    def uninstall(self) -> bool:
        """卸载备份系统"""
        logger.info("开始卸载备份系统")

        print("⚠️  即将卸载TextLoom备份系统")
        confirm = input("确认继续? (yes/no): ")

        if confirm.lower() != "yes":
            print("取消卸载")
            return False

        try:
            # 1. 停止Docker服务
            if self.docker_compose_backup.exists():
                logger.info("停止Docker备份服务")
                subprocess.run(
                    ["docker-compose", "-f", str(self.docker_compose_backup), "down"],
                    capture_output=True,
                )

            # 2. 卸载调度任务
            logger.info("卸载调度任务")
            subprocess.run(
                ["bash", str(self.scripts_dir / "backup_scheduler.sh"), "uninstall"],
                capture_output=True,
            )

            # 3. 询问是否删除备份数据
            delete_data = input("删除备份数据? (yes/no): ").lower() == "yes"

            if delete_data:
                if self.backup_dir.exists():
                    shutil.rmtree(self.backup_dir)
                    logger.info("删除备份数据")

                minio_data_dir = self.project_root / "minio_data"
                if minio_data_dir.exists():
                    shutil.rmtree(minio_data_dir)
                    logger.info("删除MinIO数据")

            # 4. 删除配置文件
            delete_config = input("删除配置文件? (yes/no): ").lower() == "yes"
            if delete_config and self.env_backup_file.exists():
                self.env_backup_file.unlink()
                logger.info("删除配置文件")

            print("✅ 备份系统卸载完成")
            return True

        except Exception as e:
            logger.error(f"卸载过程中出现错误: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom备份系统安装器")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    install_parser = subparsers.add_parser("install", help="安装备份系统")
    configure_parser = subparsers.add_parser("configure", help="交互式配置")
    validate_parser = subparsers.add_parser("validate", help="验证系统")
    uninstall_parser = subparsers.add_parser("uninstall", help="卸载系统")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    installer = BackupSystemInstaller()

    try:
        if args.command == "install":
            success = installer.install()
        elif args.command == "configure":
            success = installer.configure()
        elif args.command == "validate":
            success = installer.validate()
        elif args.command == "uninstall":
            success = installer.uninstall()
        else:
            success = False

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
