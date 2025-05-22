"""事件总线与消息处理表

Revision ID: 004_event_processing
Revises: 003_langgraph_checkpoints
Create Date: 2025-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '004_event_processing'
down_revision: Union[str, None] = '003_langgraph_checkpoints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构 - 添加事件总线和消息处理相关表"""
    
    # 创建事件类型表
    op.create_table(
        'event_types',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema', JSONB, nullable=True),  # 使用JSON Schema定义事件结构
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # 创建事件记录表
    op.create_table(
        'event_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('event_type_id', sa.Integer(), sa.ForeignKey('event_types.id'), nullable=False),
        sa.Column('event_id', sa.String(255), nullable=False, unique=True),  # Redis Stream中的事件ID
        sa.Column('stream_name', sa.String(100), nullable=False),  # Redis Stream名称
        sa.Column('payload', JSONB, nullable=False),  # 事件数据
        sa.Column('metadata', JSONB, nullable=True),  # 事件元数据
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True),
    )
    
    # 创建事件处理记录表
    op.create_table(
        'event_processing_records',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('event_log_id', UUID(as_uuid=True), sa.ForeignKey('event_logs.id'), nullable=False),
        sa.Column('consumer_group', sa.String(100), nullable=False),  # 消费者组名称
        sa.Column('consumer_name', sa.String(100), nullable=False),  # 消费者名称
        sa.Column('status', sa.String(20), nullable=False),  # 如'pending', 'processing', 'completed', 'failed'
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, default=1),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', JSONB, nullable=True),  # 处理结果
    )
    
    # 创建索引
    op.create_index(op.f('ix_event_logs_event_type_id'), 'event_logs', ['event_type_id'], unique=False)
    op.create_index(op.f('ix_event_logs_created_at'), 'event_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_event_logs_stream_name'), 'event_logs', ['stream_name'], unique=False)
    op.create_index(op.f('ix_event_processing_records_event_log_id'), 'event_processing_records', ['event_log_id'], unique=False)
    op.create_index(op.f('ix_event_processing_records_consumer_group'), 'event_processing_records', ['consumer_group'], unique=False)
    op.create_index(op.f('ix_event_processing_records_status'), 'event_processing_records', ['status'], unique=False)
    
    # 创建唯一约束
    op.create_unique_constraint('uq_event_logs_event_id', 'event_logs', ['event_id'])
    op.create_unique_constraint(
        'uq_event_processing_record_event_consumer', 
        'event_processing_records', 
        ['event_log_id', 'consumer_group', 'consumer_name']
    )


def downgrade() -> None:
    """回滚数据库结构到前一版本 - 删除事件总线和消息处理相关表"""
    op.drop_table('event_processing_records')
    op.drop_table('event_logs')
    op.drop_table('event_types') 