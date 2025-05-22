# ---------- 基础镜像 ----------
  FROM python:3.10-slim

  # 环境变量
  ENV PYTHONUNBUFFERED=1 \
      POETRY_VIRTUALENVS_IN_PROJECT=true \
      POETRY_NO_INTERACTION=1
  
  # 安装系统依赖
  RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*
  
  # 安装 Poetry（可选，也可用 pip install -r requirements.txt）
  RUN curl -sSL https://install.python-poetry.org | python3 -
  
  # 设置工作目录
  WORKDIR /app
  
  # 复制依赖配置
  COPY pyproject.toml poetry.lock* ./
  
  # 安装依赖
  RUN poetry install --only main
  
  # 复制应用源码
  COPY ./app /app
  
  # 暴露应用端口（根据实际框架修改）
  EXPOSE 8000
  
  # 默认启动命令（以 uvicorn 为例）
  CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
  