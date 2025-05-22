"""初始数据库结构

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构 - 创建初始表"""
    
    # 创建users表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建roles表
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
    )
    
    # 创建permissions表
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
    )
    
    # 创建user_roles关联表
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, primary_key=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), nullable=False, primary_key=True),
    )
    
    # 创建role_permissions关联表
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), nullable=False, primary_key=True),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id'), nullable=False, primary_key=True),
    )
    
    # 创建projects表
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # 创建project_users关联表
    op.create_table(
        'project_users',
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, primary_key=True),
        sa.Column('role', sa.String(20), nullable=False),
    )
    
    # 创建content_items表
    op.create_table(
        'content_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('content_data', JSON, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # 创建content_versions表
    op.create_table(
        'content_versions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('content_item_id', sa.Integer(), sa.ForeignKey('content_items.id'), nullable=False),
        sa.Column('version_data', JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # 创建agents表
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('config', JSON, nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建agent_states表
    op.create_table(
        'agent_states',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('state_data', JSON, nullable=False),
        sa.Column('state_type', sa.String(50), nullable=False),
        sa.Column('checkpoint_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # 创建knowledge_items表
    op.create_table(
        'knowledge_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('vector_id', sa.String(50), nullable=True),
        sa.Column('node_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # 创建knowledge_relations表
    op.create_table(
        'knowledge_relations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('source_id', sa.Integer(), sa.ForeignKey('knowledge_items.id'), nullable=False),
        sa.Column('target_id', sa.Integer(), sa.ForeignKey('knowledge_items.id'), nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('edge_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # 创建索引以提高查询性能
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_projects_created_by'), 'projects', ['created_by'], unique=False)
    op.create_index(op.f('ix_content_items_project_id'), 'content_items', ['project_id'], unique=False)
    op.create_index(op.f('ix_content_items_content_type'), 'content_items', ['content_type'], unique=False)
    op.create_index(op.f('ix_content_versions_content_item_id'), 'content_versions', ['content_item_id'], unique=False)
    op.create_index(op.f('ix_agents_project_id'), 'agents', ['project_id'], unique=False)
    op.create_index(op.f('ix_agents_agent_type'), 'agents', ['agent_type'], unique=False)
    op.create_index(op.f('ix_agent_states_agent_id'), 'agent_states', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_states_state_type'), 'agent_states', ['state_type'], unique=False)
    op.create_index(op.f('ix_knowledge_items_created_by'), 'knowledge_items', ['created_by'], unique=False)


def downgrade() -> None:
    """回滚数据库结构到前一版本 - 删除所有表"""
    # 按照依赖关系的相反顺序删除表
    op.drop_table('knowledge_relations')
    op.drop_table('knowledge_items')
    op.drop_table('agent_states')
    op.drop_table('agents')
    op.drop_table('content_versions')
    op.drop_table('content_items')
    op.drop_table('project_users')
    op.drop_table('projects')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users') 