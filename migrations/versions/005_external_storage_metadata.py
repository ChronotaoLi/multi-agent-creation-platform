"""外部存储系统元数据映射表

Revision ID: 005_external_storage_metadata
Revises: 004_event_processing
Create Date: 2025-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '005_external_storage_metadata'
down_revision: Union[str, None] = '004_event_processing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库结构 - 添加外部存储系统元数据映射表"""
    
    # 创建向量存储映射表
    op.create_table(
        'vector_store_collections',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dimension', sa.Integer(), nullable=False),
        sa.Column('index_type', sa.String(50), nullable=False),  # 如'HNSW', 'FLAT', 'IVF_FLAT'等
        sa.Column('metric_type', sa.String(50), nullable=False, default='COSINE'),  # 如'L2', 'IP', 'COSINE'等
        sa.Column('params', JSONB, nullable=True),  # 向量索引的参数
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建图数据库元数据表
    op.create_table(
        'graph_metadata',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('node_label', sa.String(100), nullable=False),  # Neo4j节点标签
        sa.Column('relationship_type', sa.String(100), nullable=True),  # Neo4j关系类型
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema', JSONB, nullable=True),  # 图模式的JSON Schema表示
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建向量存储和关系数据库的映射表
    op.create_table(
        'vector_db_mappings',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('vector_store_collections.id'), nullable=False),
        sa.Column('vector_id', sa.String(100), nullable=False),  # Milvus中的向量ID
        sa.Column('entity_type', sa.String(50), nullable=False),  # 实体类型，如'content_item', 'knowledge_item'
        sa.Column('entity_id', sa.Integer(), nullable=False),  # 关系数据库中的实体ID
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', JSONB, nullable=True),  # 额外元数据
    )
    
    # 创建图数据库和关系数据库的映射表
    op.create_table(
        'graph_db_mappings',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('graph_metadata_id', sa.Integer(), sa.ForeignKey('graph_metadata.id'), nullable=False),
        sa.Column('node_id', sa.String(100), nullable=True),  # Neo4j中的节点ID
        sa.Column('relationship_id', sa.String(100), nullable=True),  # Neo4j中的关系ID
        sa.Column('entity_type', sa.String(50), nullable=False),  # 实体类型
        sa.Column('entity_id', sa.Integer(), nullable=False),  # 关系数据库中的实体ID
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', JSONB, nullable=True),  # 额外元数据
    )
    
    # 创建索引
    op.create_index(op.f('ix_vector_db_mappings_collection_id'), 'vector_db_mappings', ['collection_id'], unique=False)
    op.create_index(op.f('ix_vector_db_mappings_vector_id'), 'vector_db_mappings', ['vector_id'], unique=True)
    op.create_index(op.f('ix_vector_db_mappings_entity_type'), 'vector_db_mappings', ['entity_type'], unique=False)
    op.create_index(op.f('ix_vector_db_mappings_entity_id'), 'vector_db_mappings', ['entity_id'], unique=False)
    
    op.create_index(op.f('ix_graph_db_mappings_graph_metadata_id'), 'graph_db_mappings', ['graph_metadata_id'], unique=False)
    op.create_index(op.f('ix_graph_db_mappings_node_id'), 'graph_db_mappings', ['node_id'], unique=True)
    op.create_index(op.f('ix_graph_db_mappings_relationship_id'), 'graph_db_mappings', ['relationship_id'], unique=True)
    op.create_index(op.f('ix_graph_db_mappings_entity_type'), 'graph_db_mappings', ['entity_type'], unique=False)
    op.create_index(op.f('ix_graph_db_mappings_entity_id'), 'graph_db_mappings', ['entity_id'], unique=False)
    
    # 创建复合索引
    op.create_index('ix_vector_db_mappings_entity', 'vector_db_mappings', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_graph_db_mappings_entity', 'graph_db_mappings', ['entity_type', 'entity_id'], unique=False)
    
    # 添加唯一约束
    op.create_unique_constraint('uq_graph_metadata_node_relation', 'graph_metadata', ['node_label', 'relationship_type'])


def downgrade() -> None:
    """回滚数据库结构到前一版本 - 删除外部存储系统元数据映射表"""
    op.drop_table('graph_db_mappings')
    op.drop_table('vector_db_mappings')
    op.drop_table('graph_metadata')
    op.drop_table('vector_store_collections') 