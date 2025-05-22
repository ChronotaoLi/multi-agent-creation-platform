"""
配置管理模块

使用Pydantic-Settings管理应用配置，支持从环境变量、配置文件等多种来源加载配置。
"""
import os
from typing import Any, Dict, List, Optional
from functools import lru_cache

from pydantic import AmqpDsn, AliasChoices, Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeManagerSettings(BaseSettings):
    """知识管理器的配置选项"""
    use_enhanced_version: bool = True
    vector_store_config: Dict[str, Any] = Field(default_factory=dict)
    graph_store_config: Dict[str, Any] = Field(default_factory=dict)
    batch_size: int = 100
    cache_enabled: bool = True
    vector_dimension: int = 1536
    collection_name: str = "knowledge"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "use_enhanced_version": self.use_enhanced_version,
            "vector_store_config": self.vector_store_config,
            "graph_store_config": self.graph_store_config,
            "batch_size": self.batch_size,
            "cache_enabled": self.cache_enabled,
            "vector_dimension": self.vector_dimension,
            "collection_name": self.collection_name,
        }


class Settings(BaseSettings):
    """应用配置类"""
    # 数据库连接配置
    database_url: PostgresDsn = Field(validation_alias='DATABASE_URL')
    # 数据库连接池配置
    db_pool_size: int = Field(default=5, validation_alias='DB_POOL_SIZE')
    db_max_overflow: int = Field(default=10, validation_alias='DB_MAX_OVERFLOW')
    
    # Redis连接配置
    redis_url: RedisDsn = Field(
        validation_alias=AliasChoices('REDIS_URL', 'CACHE_URL'),
    )
    
    # Milvus向量数据库配置
    milvus_uri: str = Field(validation_alias='MILVUS_URI')
    
    # Neo4j图数据库配置
    neo4j_uri: str = Field(validation_alias='NEO4J_URI')
    neo4j_username: str = Field(validation_alias='NEO4J_USERNAME', default="neo4j")
    neo4j_password: str = Field(validation_alias='NEO4J_PASSWORD', default="password")
    
    # API配置
    api_prefix: str = "/api/v1"
    debug: bool = False
    project_name: str = "多智能体AI创作平台"
    
    # CORS配置
    cors_origins: List[str] = Field(default_factory=list)
    
    # 日志配置
    log_level: str = "INFO"
    
    # 安全配置
    secret_key: str
    access_token_expire_minutes: int = 60
    
    # LLM配置
    langchain_llm_api_key: str = Field(validation_alias='LANGCHAIN_LLM_API_KEY')
    langchain_llm_model: str = Field(validation_alias='LANGCHAIN_LLM_MODEL', default="gpt-4")
    
    # 知识管理器配置
    knowledge_manager: KnowledgeManagerSettings = KnowledgeManagerSettings()
    
    # Celery配置
    celery_broker_url: Optional[str] = Field(validation_alias='CELERY_BROKER_URL', default=None)
    celery_result_backend: Optional[str] = Field(validation_alias='CELERY_RESULT_BACKEND', default=None)
    
    # 环境变量配置
    app_env: str = Field(validation_alias='APP_ENV', default="development")
    
    # 配置模型设置
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('APP_ENV', 'development')}"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    @field_validator("celery_broker_url", mode="before")
    def validate_celery_broker_url(cls, v: Optional[str], info) -> Optional[str]:
        """如果未设置celery_broker_url, 则使用redis_url"""
        if not v:
            redis_url = info.data.get("redis_url")
            if redis_url:
                redis_parts = str(redis_url).split("/")
                if len(redis_parts) > 3:
                    # 使用Redis的1号数据库作为Celery的broker
                    redis_parts[-1] = "1"
                    return "/".join(redis_parts)
        return v
    
    @field_validator("celery_result_backend", mode="before")
    def validate_celery_result_backend(cls, v: Optional[str], info) -> Optional[str]:
        """如果未设置celery_result_backend, 则使用redis_url"""
        if not v:
            redis_url = info.data.get("redis_url")
            if redis_url:
                redis_parts = str(redis_url).split("/")
                if len(redis_parts) > 3:
                    # 使用Redis的2号数据库作为Celery的结果存储
                    redis_parts[-1] = "2"
                    return "/".join(redis_parts)
        return v
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """自定义配置加载优先级
        
        优先顺序：
        1. 初始化参数
        2. 环境变量
        3. 环境文件
        4. 密钥文件
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例实例"""
    return Settings()
