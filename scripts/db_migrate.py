#!/usr/bin/env python
"""
数据库迁移脚本

提供数据库迁移的命令行工具，支持升级、降级和版本信息查询
"""
import os
import sys
import argparse
import asyncio
from pathlib import Path

# 将项目根目录添加到Python路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from alembic.config import Config
from alembic import command
from app.core.config import get_settings


def get_alembic_config():
    """获取Alembic配置"""
    # 创建Alembic配置对象
    config_path = ROOT_DIR / "migrations" / "alembic.ini"
    config = Config(str(config_path) if config_path.exists() else None)
    
    # 如果配置文件不存在，设置必要的配置
    if not config_path.exists():
        config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
        config.set_main_option("sqlalchemy.url", str(get_settings().database_url))
        config.set_main_option("prepend_sys_path", ".")
        
    return config


def upgrade(args):
    """升级数据库结构
    
    Args:
        args: 命令行参数，包含--revision用于指定版本
    """
    config = get_alembic_config()
    revision = args.revision or "head"
    print(f"升级数据库到版本: {revision}")
    command.upgrade(config, revision)
    print("升级完成!")


def downgrade(args):
    """降级数据库结构
    
    Args:
        args: 命令行参数，包含--revision用于指定版本
    """
    config = get_alembic_config()
    revision = args.revision or "-1"
    print(f"降级数据库到版本: {revision}")
    if args.force or input("警告: 降级可能会导致数据丢失。是否继续? (y/N): ").lower() == "y":
        command.downgrade(config, revision)
        print("降级完成!")
    else:
        print("操作已取消")


def revision(args):
    """创建新的迁移脚本
    
    Args:
        args: 命令行参数，包含--message用于指定迁移消息
    """
    config = get_alembic_config()
    message = args.message
    if not message:
        print("错误: 必须提供迁移消息")
        return
    
    print(f"创建新的迁移脚本: {message}")
    command.revision(config, message=message, autogenerate=args.autogenerate)
    print("迁移脚本创建完成!")


def version(args):
    """显示当前数据库版本信息
    
    Args:
        args: 命令行参数
    """
    config = get_alembic_config()
    print("数据库版本信息:")
    command.current(config, verbose=True)


def main():
    """脚本主入口"""
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    subparsers = parser.add_subparsers(title="命令", dest="command")
    
    # 升级命令
    upgrade_parser = subparsers.add_parser("upgrade", help="升级数据库结构")
    upgrade_parser.add_argument("--revision", help="目标版本 (默认: head)")
    upgrade_parser.set_defaults(func=upgrade)
    
    # 降级命令
    downgrade_parser = subparsers.add_parser("downgrade", help="降级数据库结构")
    downgrade_parser.add_argument("--revision", help="目标版本 (默认: -1)")
    downgrade_parser.add_argument("--force", action="store_true", help="强制执行，不提示确认")
    downgrade_parser.set_defaults(func=downgrade)
    
    # 新建迁移脚本命令
    revision_parser = subparsers.add_parser("revision", help="创建新的迁移脚本")
    revision_parser.add_argument("--message", "-m", required=True, help="迁移消息")
    revision_parser.add_argument("--autogenerate", "-a", action="store_true", help="自动生成迁移脚本")
    revision_parser.set_defaults(func=revision)
    
    # 版本信息命令
    version_parser = subparsers.add_parser("version", help="显示当前数据库版本")
    version_parser.set_defaults(func=version)
    
    args = parser.parse_args()
    
    if not hasattr(args, "func"):
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main() 