#!/usr/bin/env python
"""
数据填充脚本

根据定义的数据模型生成测试数据，填充数据库。
"""
import argparse
import asyncio
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.data_access.db_session import AsyncSessionLocal, get_db
from app.models.domain.user import User
from app.models.domain.role import Role, UserRole
from app.models.domain.project import Project, ProjectUser
from app.models.domain.content import ContentItem, ContentVersion
from app.models.domain.knowledge import KnowledgeItem
from app.models.domain.agent import Agent
from app.utils.common_utils import generate_ulid, get_utc_now

# 获取应用配置
settings = get_settings()


async def generate_roles() -> List[Role]:
    """生成角色数据

    Returns:
        List[Role]: 角色对象列表
    """
    roles = [
        Role(name="admin", description="系统管理员"),
        Role(name="content_creator", description="内容创作者"),
        Role(name="editor", description="编辑"),
        Role(name="viewer", description="浏览者"),
    ]
    
    return roles


async def generate_users(count: int, roles: List[Role]) -> List[Tuple[User, List[Role]]]:
    """生成用户数据

    Args:
        count: 用户数量
        roles: 角色列表

    Returns:
        List[Tuple[User, List[Role]]]: 用户对象和对应角色列表的元组
    """
    users_with_roles = []
    
    # 确保有一个管理员用户
    admin_user = User(
        username="admin",
        email="admin@example.com",
        display_name="系统管理员",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
    )
    users_with_roles.append((admin_user, [roles[0]]))  # 分配管理员角色
    
    # 生成普通用户
    for i in range(1, count):
        user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            display_name=f"用户 {i}",
            hashed_password=get_password_hash(f"password{i}"),
            is_active=True,
        )
        
        # 随机分配1-2个角色（不包括管理员角色）
        user_roles = random.sample(roles[1:], k=random.randint(1, min(2, len(roles)-1)))
        users_with_roles.append((user, user_roles))
    
    return users_with_roles


async def generate_projects(count: int, users: List[User]) -> List[Tuple[Project, List[Tuple[User, str]]]]:
    """生成项目数据

    Args:
        count: 项目数量
        users: 用户列表

    Returns:
        List[Tuple[Project, List[Tuple[User, str]]]]: 项目对象和用户角色元组列表的元组
    """
    projects_with_users = []
    
    project_types = ["文学创作", "剧本创作", "广告文案", "游戏剧情", "科技论文"]
    project_statuses = ["active", "archived", "draft"]
    
    for i in range(count):
        creator = random.choice(users)
        
        created_at = get_utc_now() - timedelta(days=random.randint(1, 30))
        updated_at = created_at + timedelta(days=random.randint(0, 10))
        
        project = Project(
            title=f"项目 {i + 1}",
            description=f"这是项目 {i + 1} 的描述，用于测试目的。",
            project_type=random.choice(project_types),
            status=random.choice(project_statuses),
            created_at=created_at,
            updated_at=updated_at,
            created_by=creator.id,
        )
        
        # 为项目添加用户（包括创建者）
        project_users = [(creator, "owner")]
        
        # 随机添加2-4个协作者
        collaborators = random.sample(
            [u for u in users if u.id != creator.id],
            k=min(random.randint(2, 4), len(users) - 1),
        )
        
        # 为协作者分配角色
        for collaborator in collaborators:
            role = random.choice(["editor", "viewer", "contributor"])
            project_users.append((collaborator, role))
        
        projects_with_users.append((project, project_users))
    
    return projects_with_users


async def generate_content_items(projects: List[Project], users: List[User]) -> List[Tuple[ContentItem, List[Dict[str, Any]]]]:
    """生成内容数据

    Args:
        projects: 项目列表
        users: 用户列表

    Returns:
        List[Tuple[ContentItem, List[Dict[str, Any]]]]: 内容项和版本列表的元组
    """
    content_items_with_versions = []
    
    content_types = ["outline", "chapter", "scene", "character", "concept"]
    
    # 每个项目生成2-5个内容项
    for project in projects:
        num_items = random.randint(2, 5)
        
        for i in range(num_items):
            content_type = random.choice(content_types)
            creator = random.choice(users)
            
            created_at = project.created_at + timedelta(days=random.randint(1, 5))
            updated_at = created_at + timedelta(days=random.randint(0, 5))
            
            # 根据内容类型生成不同的内容数据
            content_data = {}
            if content_type == "outline":
                content_data = {
                    "sections": [f"第{j+1}章：示例章节标题" for j in range(random.randint(3, 8))],
                    "synopsis": "这是一个示例大纲，用于测试目的。"
                }
            elif content_type == "chapter":
                content_data = {
                    "title": f"第{random.randint(1, 10)}章：示例章节",
                    "content": "这是章节内容，包含多个段落。\n\n这是第二个段落，用于测试排版。",
                    "notes": "编辑笔记：需要扩展第二段落。"
                }
            elif content_type == "character":
                content_data = {
                    "name": f"角色{i+1}",
                    "age": random.randint(18, 60),
                    "description": "这是角色描述，用于测试目的。",
                    "traits": ["勇敢", "聪明", "固执"]
                }
            else:
                content_data = {
                    "title": f"{content_type.capitalize()} {i+1}",
                    "description": f"这是{content_type}描述，用于测试目的。"
                }
            
            content_item = ContentItem(
                title=f"{content_type.capitalize()} {i+1}",
                content_type=content_type,
                content_data=content_data,
                project_id=project.id,
                created_at=created_at,
                updated_at=updated_at,
                created_by=creator.id,
            )
            
            # 为内容项生成1-3个版本
            versions = []
            for v in range(1, random.randint(2, 4)):
                version_created_at = content_item.created_at + timedelta(days=v)
                editor = random.choice(users)
                
                # 复制原内容并稍作修改
                version_data = content_data.copy()
                if content_type == "outline" and "sections" in version_data:
                    version_data["sections"].append(f"新章节 {v}")
                elif content_type == "chapter" and "content" in version_data:
                    version_data["content"] += f"\n\n这是版本{v}的新段落。"
                
                versions.append({
                    "version_data": version_data,
                    "created_at": version_created_at,
                    "created_by": editor.id
                })
            
            content_items_with_versions.append((content_item, versions))
    
    return content_items_with_versions


async def generate_knowledge_items(count: int, users: List[User]) -> List[KnowledgeItem]:
    """生成知识库数据

    Args:
        count: 知识项数量
        users: 用户列表

    Returns:
        List[KnowledgeItem]: 知识项对象列表
    """
    knowledge_items = []
    
    knowledge_categories = ["writing_tips", "character_archetypes", "plot_structures", "worldbuilding", "literary_terms"]
    
    for i in range(count):
        creator = random.choice(users)
        category = random.choice(knowledge_categories)
        
        created_at = get_utc_now() - timedelta(days=random.randint(1, 30))
        updated_at = created_at + timedelta(days=random.randint(0, 10))
        
        # 元数据
        metadata = {
            "category": category,
            "tags": random.sample(["创作", "技巧", "参考", "示例", "理论"], k=random.randint(1, 3)),
            "source": random.choice(["内部", "外部", "用户贡献"]),
            "importance": random.randint(1, 5)
        }
        
        knowledge_item = KnowledgeItem(
            title=f"知识项 {i+1} - {category}",
            content=f"这是关于{category}的知识内容。\n\n包含多个段落的详细说明和示例。\n\n这是第三个段落，用于测试格式。",
            metadata=metadata,
            vector_id=f"vec_{generate_ulid()}" if random.random() > 0.3 else None,
            node_id=f"node_{generate_ulid()}" if random.random() > 0.3 else None,
            created_at=created_at,
            updated_at=updated_at,
            created_by=creator.id,
        )
        
        knowledge_items.append(knowledge_item)
    
    return knowledge_items


async def generate_agents(projects: List[Project]) -> List[Agent]:
    """生成智能体数据

    Args:
        projects: 项目列表

    Returns:
        List[Agent]: 智能体对象列表
    """
    agents = []
    
    agent_types = ["editor", "character_designer", "plot_generator", "dialogue_writer", "world_builder"]
    
    # 为每个项目生成1-3个智能体
    for project in projects:
        num_agents = random.randint(1, 3)
        
        for i in range(num_agents):
            agent_type = random.choice(agent_types)
            
            # 根据智能体类型生成配置
            config = {
                "llm_model": random.choice(["gpt-3.5-turbo", "gpt-4", "claude-2"]),
                "temperature": round(random.uniform(0.0, 1.0), 1),
                "max_tokens": random.choice([1024, 2048, 4096]),
                "system_prompt": f"你是一个专业的{agent_type}智能体，负责协助用户完成创作任务。"
            }
            
            # 为不同类型的智能体添加特定配置
            if agent_type == "editor":
                config["editing_style"] = random.choice(["严格", "宽松", "创意"])
                config["focus_areas"] = random.sample(["语法", "结构", "内容", "风格", "连贯性"], k=random.randint(2, 5))
            elif agent_type == "character_designer":
                config["archetype_database"] = True
                config["personality_dimensions"] = ["外向性", "开放性", "尽责性", "宜人性", "神经质"]
            
            agent = Agent(
                name=f"{agent_type.replace('_', ' ').title()} {i+1}",
                agent_type=agent_type,
                config=config,
                project_id=project.id,
                created_at=project.created_at + timedelta(days=random.randint(0, 5)),
                updated_at=project.updated_at,
            )
            
            agents.append(agent)
    
    return agents


async def seed_database(db: AsyncSession, count: int = 10) -> None:
    """填充数据库

    Args:
        db: 数据库会话
        count: 用户数量基准
    """
    print(f"正在生成测试数据，基准数量：{count}...")
    
    try:
        # 生成角色
        roles = await generate_roles()
        db.add_all(roles)
        await db.flush()
        
        # 生成用户和关联角色
        users_with_roles = await generate_users(count, roles)
        users = []
        
        for user, user_roles in users_with_roles:
            db.add(user)
            users.append(user)
        
        await db.flush()
        
        # 创建用户-角色关联
        for user, user_roles in users_with_roles:
            for role in user_roles:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                db.add(user_role)
        
        await db.flush()
        
        # 生成项目及关联用户
        projects_with_users = await generate_projects(count, users)
        projects = []
        
        for project, project_users in projects_with_users:
            db.add(project)
            projects.append(project)
        
        await db.flush()
        
        # 创建项目-用户关联
        for project, project_users in projects_with_users:
            for user, role in project_users:
                project_user = ProjectUser(
                    project_id=project.id,
                    user_id=user.id,
                    role=role
                )
                db.add(project_user)
        
        await db.flush()
        
        # 生成内容项及版本
        content_items_with_versions = await generate_content_items(projects, users)
        
        for content_item, versions in content_items_with_versions:
            db.add(content_item)
            await db.flush()
            
            # 创建内容版本
            for version_data in versions:
                content_version = ContentVersion(
                    content_item_id=content_item.id,
                    version_data=version_data["version_data"],
                    created_at=version_data["created_at"],
                    created_by=version_data["created_by"]
                )
                db.add(content_version)
        
        await db.flush()
        
        # 生成知识库项
        knowledge_items = await generate_knowledge_items(count * 2, users)
        db.add_all(knowledge_items)
        await db.flush()
        
        # 生成智能体
        agents = await generate_agents(projects)
        db.add_all(agents)
        
        # 提交所有更改
        await db.commit()
        
        print("数据库填充成功！")
        
        # 输出统计信息
        print(f"已创建：")
        print(f"- {len(roles)} 个角色")
        print(f"- {len(users)} 个用户")
        print(f"- {len(projects)} 个项目")
        print(f"- {len(content_items_with_versions)} 个内容项")
        print(f"- {sum(len(versions) for _, versions in content_items_with_versions)} 个内容版本")
        print(f"- {len(knowledge_items)} 个知识项")
        print(f"- {len(agents)} 个智能体")
        
    except Exception as e:
        await db.rollback()
        print(f"填充数据库时发生错误: {e}")
        raise


async def export_data_to_json(
    users: List[User],
    roles: List[Role],
    projects: List[Project],
    content_items: List[ContentItem],
    knowledge_items: List[KnowledgeItem],
    agents: List[Agent],
    output_dir: str
) -> None:
    """将数据导出为JSON文件

    Args:
        users: 用户列表
        roles: 角色列表
        projects: 项目列表
        content_items: 内容项列表
        knowledge_items: 知识项列表
        agents: 智能体列表
        output_dir: 输出目录
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 准备导出数据
    export_data = {
        "users": [user.to_dict() for user in users],
        "roles": [role.to_dict() for role in roles],
        "projects": [project.to_dict() for project in projects],
        "content_items": [item.to_dict() for item in content_items],
        "knowledge_items": [item.to_dict() for item in knowledge_items],
        "agents": [agent.to_dict() for agent in agents],
    }
    
    # 导出数据
    for key, items in export_data.items():
        file_path = output_path / f"{key}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        print(f"已导出 {len(items)} 条 {key} 数据到 {file_path}")


async def seed_and_export(
    count: int = 10, 
    export: bool = False, 
    output_dir: str = "seed_data"
) -> None:
    """生成数据并可选导出

    Args:
        count: 用户数量基准
        export: 是否导出JSON
        output_dir: 导出目录
    """
    async with AsyncSessionLocal() as session:
        await seed_database(session, count)
        
        if export:
            # 查询所有实体以导出
            users = (await session.execute(select(User))).scalars().all()
            roles = (await session.execute(select(Role))).scalars().all()
            projects = (await session.execute(
                select(Project).options(selectinload(Project.project_users))
            )).scalars().all()
            content_items = (await session.execute(
                select(ContentItem).options(selectinload(ContentItem.versions))
            )).scalars().all()
            knowledge_items = (await session.execute(select(KnowledgeItem))).scalars().all()
            agents = (await session.execute(select(Agent))).scalars().all()
            
            await export_data_to_json(
                users, roles, projects, content_items, knowledge_items, agents, output_dir
            )


async def clear_database() -> None:
    """清空数据库表"""
    print("正在清空数据库...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 删除顺序要考虑外键约束
            await session.execute("DELETE FROM content_versions")
            await session.execute("DELETE FROM content_items")
            await session.execute("DELETE FROM knowledge_items")
            await session.execute("DELETE FROM agents")
            await session.execute("DELETE FROM project_users")
            await session.execute("DELETE FROM projects")
            await session.execute("DELETE FROM user_roles")
            await session.execute("DELETE FROM users")
            await session.execute("DELETE FROM roles")
            
            await session.commit()
            print("数据库已清空")
        except Exception as e:
            await session.rollback()
            print(f"清空数据库时发生错误: {e}")
            raise


async def reset_database(count: int = 10) -> None:
    """重置数据库（清空并重新填充）

    Args:
        count: 基准数量
    """
    await clear_database()
    async with AsyncSessionLocal() as session:
        await seed_database(session, count)


async def run_action(action: str, count: int, output_dir: str) -> None:
    """运行指定操作

    Args:
        action: 操作类型
        count: 基准数量
        output_dir: 导出目录
    """
    if action == "seed":
        async with AsyncSessionLocal() as session:
            await seed_database(session, count)
    elif action == "clear":
        await clear_database()
    elif action == "reset":
        await reset_database(count)
    elif action == "export":
        await seed_and_export(count, export=True, output_dir=output_dir)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库数据填充工具")
    parser.add_argument(
        "--action",
        choices=["seed", "clear", "reset", "export"],
        default="seed",
        help="执行操作",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="基准生成数量",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="seed_data",
        help="数据导出目录（仅用于export操作）",
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_action(args.action, args.count, args.output_dir))
    except Exception as e:
        print(f"执行操作时发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
