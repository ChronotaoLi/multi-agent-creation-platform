"""LangGraph检查点存储

Revision ID: 003_langgraph_checkpoints
Revises: 002_initial_data
Create Date: 2025-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '003_langgraph_checkpoints'
down_revision: Union[str, None] = '002_initial_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构 - 添加LangGraph检查点表"""
    
    # 为LangGraph的PostgresSaver创建检查点表
    op.create_table(
        'langgraph_checkpoints',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('thread_id', sa.String(255), nullable=False, index=True),
        sa.Column('checkpoint_id', sa.String(255), nullable=False, index=True),
        sa.Column('state_dict', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', JSONB, nullable=True),
    )
    
    # 添加唯一索引确保thread_id和checkpoint_id的组合唯一
    op.create_index(
        'uq_langgraph_checkpoints_thread_checkpoint',
        'langgraph_checkpoints',
        ['thread_id', 'checkpoint_id'],
        unique=True
    )
    
    # 创建工作流运行记录表
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('workflow_type', sa.String(50), nullable=False, index=True),
        sa.Column('thread_id', sa.String(255), nullable=False, unique=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='running'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('config', JSONB, nullable=False),
        sa.Column('latest_checkpoint_id', sa.String(255), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
    )
    
    # 创建工作流干预表，用于记录人机协作中的干预行为
    op.create_table(
        'workflow_interventions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('workflow_run_id', sa.Integer(), sa.ForeignKey('workflow_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('intervention_type', sa.String(50), nullable=False),
        sa.Column('user_input', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )
    
    # 添加索引
    op.create_index(op.f('ix_workflow_runs_project_id'), 'workflow_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_workflow_interventions_workflow_run_id'), 'workflow_interventions', ['workflow_run_id'], unique=False)


def downgrade() -> None:
    """回滚数据库结构到前一版本 - 删除LangGraph检查点表"""
    op.drop_table('workflow_interventions')
    op.drop_table('workflow_runs')
    op.drop_table('langgraph_checkpoints') 