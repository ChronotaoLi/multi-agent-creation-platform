# 多智能体AI创作平台

多智能体AI创作平台是一个基于大型语言模型（LLM）的创作辅助系统，通过多智能体协作完成复杂创作任务。

## 功能特性

- 多智能体协作：专家智能体分工合作，共同完成创作任务
- 知识管理：支持知识库建设、向量检索和图谱存储
- 工作流编排：可视化定义智能体协作流程
- API接口：提供丰富的REST API和WebSocket实时通信
- 可扩展性：支持横向扩展以处理高并发请求

## 技术栈

- **后端框架**：FastAPI
- **数据库**：PostgreSQL
- **缓存**：Redis
- **向量存储**：Milvus
- **图存储**：Neo4j
- **任务队列**：Celery
- **智能体框架**：LangGraph

## 开始使用

### 安装依赖

1. 确保已安装Python 3.10或更高版本
2. 安装Poetry包管理器
3. 克隆仓库并安装依赖：

```bash
# 安装依赖
cd multi_agent_creation_platform
poetry install
```

### 设置环境

```bash
# 复制环境变量示例文件
cp .env示例 .env

# 编辑.env文件，配置必要的环境变量
# 重要：请确保在 .env 文件中设置了 SECRET_KEY，这是一个用于保障应用安全的随机字符串。
# 例如：SECRET_KEY=your_strong_random_secret_key_here
```

### 启动依赖服务

```bash
# 启动服务（需要Docker和Docker Compose）
python scripts/start_services.py --action start
```

# 配置说明：
# - Celery: 如果未在 .env 文件中明确配置 `CELERY_BROKER_URL` 和 `CELERY_RESULT_BACKEND`，
#   系统将默认使用 Redis 服务（与主缓存 Redis 分别使用不同的数据库编号）。
#   `CELERY_BROKER_URL` 将使用 Redis DB 1，`CELERY_RESULT_BACKEND` 将使用 Redis DB 2。

### 初始化数据库

```bash
# 初始化数据库结构并填充基础数据
python scripts/init_db.py

# 创建一个管理员用户
python scripts/init_db.py --create-admin --admin-username admin --admin-password secure_password --admin-email admin@example.com
```

### 管理数据库迁移

```bash
# 查看当前数据库版本
python scripts/db_migrate.py version

# 升级数据库到最新版本
python scripts/db_migrate.py upgrade

# 创建新的迁移脚本
python scripts/db_migrate.py revision -m "新的变更描述" -a

# 降级数据库到特定版本
python scripts/db_migrate.py downgrade --revision 001_initial_schema
```

### 运行应用

```bash
# 激活虚拟环境
poetry shell

# 运行应用
python -m app.main
```

应用启动后，可以访问以下URL：

- API文档：http://localhost:8000/docs
- ReDoc文档：http://localhost:8000/api/redoc

## 开发指南

### 目录结构

```
multi_agent_creation_platform/
├── app/                                # FastAPI应用核心目录
│   ├── __init__.py                     # 包标识文件
│   ├── main.py                         # FastAPI应用入口，配置全局中间件、启动/关闭事件和异常处理器
│   ├── agents/                         # 智能体定义和实现
│   ├── api/                            # API路由和处理器
│   ├── core/                           # 核心配置和初始化
│   ├── data_access/                    # 数据访问层
│   ├── models/                         # 数据模型
│   ├── services/                       # 业务服务
│   ├── utils/                          # 工具函数
│   └── workflows/                      # 工作流定义
├── migrations/                         # 数据库迁移
│   ├── versions/                       # 迁移版本脚本
│   ├── env.py                          # Alembic环境配置
│   ├── script.py.mako                  # 迁移脚本模板
│   ├── alembic.ini                     # Alembic配置
│   └── README.md                       # 迁移说明文档
├── scripts/                            # 脚本工具
│   ├── db_migrate.py                   # 数据库迁移工具
│   ├── init_db.py                      # 数据库初始化工具
│   └── start_services.py               # 服务管理工具
└── tests/                              # 测试代码
    ├── unit/                           # 单元测试
    ├── integration/                    # 集成测试
    └── e2e/                            # 端到端测试
```

### 数据模型变更流程

当需要修改数据模型时，请遵循以下步骤：

1. 在`app/models/domain/`中更新模型定义
2. 创建新的迁移脚本：`python scripts/db_migrate.py revision -m "描述变更" -a`
3. 检查生成的迁移脚本，确保其正确反映了所需的变更
4. 应用迁移：`python scripts/db_migrate.py upgrade`
5. 在对应的Repository中更新相关查询代码

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行单元测试
python -m pytest tests/unit

# 运行集成测试
python -m pytest tests/integration

# 运行端到端测试
python -m pytest tests/e2e

# 运行特定测试文件
python -m pytest tests/path/to/test_file.py

# 运行特定测试用例
python -m pytest tests/path/to/test_file.py::TestClass::test_method

# 显示详细输出
python -m pytest -v
```

## 贡献

欢迎贡献代码、提交问题或建议。请确保在提交Pull Request前运行测试并遵循代码规范。

## 许可证

本项目采用MIT许可证。

