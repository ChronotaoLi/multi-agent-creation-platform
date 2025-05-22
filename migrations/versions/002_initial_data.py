"""初始数据填充

Revision ID: 002_initial_data
Revises: 001_initial_schema
Create Date: 2025-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '002_initial_data'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构 - 添加初始数据"""
    
    # 定义表结构（不创建表，仅用于插入数据）
    roles_table = table('roles',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.String),
    )
    
    permissions_table = table('permissions',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.String),
    )
    
    role_permissions_table = table('role_permissions',
        column('role_id', sa.Integer),
        column('permission_id', sa.Integer),
    )
    
    # 插入基础角色
    op.bulk_insert(roles_table,
        [
            {'id': 1, 'name': 'admin', 'description': '系统管理员角色'},
            {'id': 2, 'name': 'creator', 'description': '创作者角色'},
            {'id': 3, 'name': 'viewer', 'description': '查看者角色'},
        ]
    )
    
    # 插入基础权限
    op.bulk_insert(permissions_table,
        [
            {'id': 1, 'name': 'user:manage', 'description': '管理用户'},
            {'id': 2, 'name': 'project:create', 'description': '创建项目'},
            {'id': 3, 'name': 'project:edit', 'description': '编辑项目'},
            {'id': 4, 'name': 'project:delete', 'description': '删除项目'},
            {'id': 5, 'name': 'project:view', 'description': '查看项目'},
            {'id': 6, 'name': 'content:create', 'description': '创建内容'},
            {'id': 7, 'name': 'content:edit', 'description': '编辑内容'},
            {'id': 8, 'name': 'content:delete', 'description': '删除内容'},
            {'id': 9, 'name': 'content:view', 'description': '查看内容'},
            {'id': 10, 'name': 'agent:manage', 'description': '管理智能体'},
            {'id': 11, 'name': 'knowledge:manage', 'description': '管理知识库'},
            {'id': 12, 'name': 'system:config', 'description': '系统配置管理'},
        ]
    )
    
    # 为角色分配权限
    op.bulk_insert(role_permissions_table,
        [
            # admin角色拥有所有权限
            {'role_id': 1, 'permission_id': 1},
            {'role_id': 1, 'permission_id': 2},
            {'role_id': 1, 'permission_id': 3},
            {'role_id': 1, 'permission_id': 4},
            {'role_id': 1, 'permission_id': 5},
            {'role_id': 1, 'permission_id': 6},
            {'role_id': 1, 'permission_id': 7},
            {'role_id': 1, 'permission_id': 8},
            {'role_id': 1, 'permission_id': 9},
            {'role_id': 1, 'permission_id': 10},
            {'role_id': 1, 'permission_id': 11},
            {'role_id': 1, 'permission_id': 12},
            
            # creator角色拥有项目和内容相关权限
            {'role_id': 2, 'permission_id': 2},
            {'role_id': 2, 'permission_id': 3},
            {'role_id': 2, 'permission_id': 5},
            {'role_id': 2, 'permission_id': 6},
            {'role_id': 2, 'permission_id': 7},
            {'role_id': 2, 'permission_id': 9},
            {'role_id': 2, 'permission_id': 10},
            
            # viewer角色仅拥有查看权限
            {'role_id': 3, 'permission_id': 5},
            {'role_id': 3, 'permission_id': 9},
        ]
    )


def downgrade() -> None:
    """回滚数据库结构到前一版本 - 删除初始数据"""
    # 清空role_permissions表中的数据
    op.execute("DELETE FROM role_permissions")
    
    # 清空permissions表中的数据
    op.execute("DELETE FROM permissions")
    
    # 清空roles表中的数据
    op.execute("DELETE FROM roles") 