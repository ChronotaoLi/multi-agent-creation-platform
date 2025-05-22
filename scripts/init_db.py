#!/usr/bin/env python
"""
数据库初始化脚本

首次设置项目时，初始化数据库结构并填充必要数据
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path

# 将项目根目录添加到Python路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy_utils import database_exists, create_database
from alembic.config import Config
from alembic import command
from sqlalchemy import text

from app.core.config import get_settings


async def create_db_if_not_exists():
    """创建数据库（如果不存在）"""
    settings = get_settings()
    db_url = str(settings.database_url)
    
    # 创建临时引擎用于检查数据库是否存在
    async_url = db_url
    sync_url = db_url.replace('+asyncpg', '')
    
    # 检查数据库是否存在，不存在则创建
    if not database_exists(sync_url):
        print(f"数据库不存在，正在创建: {db_url}")
        create_database(sync_url)
        print("数据库创建成功!")
    else:
        print(f"数据库已存在: {db_url}")
    
    return True


def run_migrations(args):
    """运行数据库迁移"""
    config = Config(str(ROOT_DIR / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
    
    # 运行迁移
    print("正在应用迁移...")
    command.upgrade(config, "head")
    print("迁移应用完成!")


def init_data(args):
    """初始化示例管理员用户"""
    # 这部分工作由迁移脚本002_initial_data.py完成
    print("基础权限和角色数据已通过迁移脚本应用")
    
    # 如果需要创建管理员用户，可以在这里添加代码
    if args.create_admin:
        print("正在创建管理员用户...")
        asyncio.run(create_admin_user(args.admin_username, args.admin_password, args.admin_email))


async def create_admin_user(username, password, email):
    """创建管理员用户
    
    Args:
        username: 管理员用户名
        password: 管理员密码
        email: 管理员电子邮件
    """
    try:
        # 导入所需模块
        from app.data_access.db_session import AsyncSessionLocal
        from app.models.domain import User, Role, UserRole
        from app.core.security import get_password_hash
        
        # 创建数据库会话
        async with AsyncSessionLocal() as session:
            # 检查用户是否已存在
            user = await session.execute(
                text("SELECT id FROM users WHERE username = :username OR email = :email"),
                {"username": username, "email": email}
            )
            user = user.scalar_one_or_none()
            
            if user:
                print(f"用户 {username} 已存在，跳过创建")
                return
            
            # 获取admin角色
            role = await session.execute(
                text("SELECT id FROM roles WHERE name = 'admin'")
            )
            role_id = role.scalar_one()
            
            # 创建新管理员用户
            hashed_password = get_password_hash(password)
            user_query = """
            INSERT INTO users (username, email, hashed_password, display_name, is_active) 
            VALUES (:username, :email, :hashed_password, :display_name, TRUE)
            RETURNING id
            """
            user_id = await session.execute(
                text(user_query), 
                {
                    "username": username,
                    "email": email,
                    "hashed_password": hashed_password,
                    "display_name": "系统管理员"
                }
            )
            user_id = user_id.scalar_one()
            
            # 关联用户和角色
            await session.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
                {"user_id": user_id, "role_id": role_id}
            )
            
            await session.commit()
            print(f"管理员用户 {username} 创建成功!")
    except Exception as e:
        print(f"创建管理员用户失败: {str(e)}")
        raise


def main():
    """脚本主入口"""
    parser = argparse.ArgumentParser(description="数据库初始化工具")
    parser.add_argument("--create-admin", action="store_true", help="创建管理员用户")
    parser.add_argument("--admin-username", default="admin", help="管理员用户名，默认为'admin'")
    parser.add_argument("--admin-password", default="admin", help="管理员密码，默认为'admin'")
    parser.add_argument("--admin-email", default="admin@example.com", help="管理员电子邮件，默认为'admin@example.com'")
    args = parser.parse_args()
    
    print("=== 开始数据库初始化 ===")
    
    # 创建数据库（如果不存在）
    asyncio.run(create_db_if_not_exists())
    
    # 运行所有迁移
    run_migrations(args)
    
    # 初始化基础数据
    init_data(args)
    
    print("=== 数据库初始化完成 ===")


if __name__ == "__main__":
    main() 