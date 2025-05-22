# 数据库迁移系统

本目录包含多智能体AI创作平台的数据库迁移脚本，使用Alembic管理数据库结构的演化。

## 迁移脚本概述

迁移脚本按顺序编号，每个脚本负责数据库结构的特定变更：

1. **001_initial_schema.py**: 创建初始数据库表结构
2. **002_initial_data.py**: 填充基础数据（角色、权限等）
3. **003_langgraph_checkpoints.py**: 创建LangGraph检查点存储相关表
4. **004_event_processing.py**: 创建事件总线和消息处理相关表
5. **005_external_storage_metadata.py**: 创建外部存储系统元数据映射表

## 使用方法

通过项目根目录下的`scripts/db_migrate.py`脚本执行迁移操作。以下是常用命令：

### 升级数据库到最新版本

```bash
python scripts/db_migrate.py upgrade
```

### 升级到特定版本

```bash
python scripts/db_migrate.py upgrade --revision 003_langgraph_checkpoints
```

### 降级数据库

```bash
python scripts/db_migrate.py downgrade --revision 001_initial_schema
```

### 查看当前数据库版本

```bash
python scripts/db_migrate.py version
```

### 创建新的迁移脚本

手动创建新的迁移脚本：

```bash
python scripts/db_migrate.py revision -m "描述变更内容"
```

从模型自动生成迁移脚本：

```bash
python scripts/db_migrate.py revision -m "描述变更内容" -a
```

## 数据库配置

数据库连接信息从应用配置中获取。确保在运行迁移脚本前已正确设置以下环境变量或`.env`文件中的配置：

```
DATABASE_URL=postgresql://username:password@host:port/database
```

## 注意事项

1. 在生产环境执行迁移前，请先备份数据库
2. 降级操作可能会导致数据丢失，请谨慎操作
3. 自动生成的迁移脚本可能需要手动调整
4. 确保迁移脚本的幂等性，即重复执行不会导致错误

## 外部存储系统

本项目使用PostgreSQL作为主数据库，同时还使用：

- **Milvus**: 向量数据库，用于语义搜索与嵌入存储
- **Neo4j**: 图数据库，用于存储知识图谱和角色关系网络
- **Redis**: 用于缓存、事件总线和Celery任务队列

这些外部系统的设置不在数据库迁移范围内，需要单独配置。 