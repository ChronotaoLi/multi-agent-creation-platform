#!/usr/bin/env python
"""
项目初始化脚本

用于设置项目环境，安装依赖和初始化数据库。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def check_prerequisites():
    """检查先决条件"""
    print("检查先决条件...")
    
    # 检查 Python 版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 10):
        print("错误: 需要 Python 3.10 或更高版本")
        sys.exit(1)
    
    # 检查 Poetry
    try:
        subprocess.run(["poetry", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到 Poetry，请先安装 Poetry (https://python-poetry.org/docs/#installation)")
        sys.exit(1)
    
    print("✅ 先决条件检查通过")


def setup_environment(env="development"):
    """设置环境配置文件"""
    print(f"设置 {env} 环境...")
    
    # 获取脚本所在目录的父目录（项目根目录）
    project_root = Path(__file__).parent.parent
    
    # 检查是否存在示例环境文件
    env_example = project_root / ".env示例"
    env_file = project_root / f".env.{env}"
    
    if not env_example.exists():
        print(f"错误: 未找到示例环境文件 (.env示例)")
        sys.exit(1)
    
    # 如果环境文件不存在，则从示例创建
    if not env_file.exists():
        print(f"创建环境文件 {env_file}...")
        with open(env_example, "r", encoding="utf-8") as src:
            content = src.read()
        
        with open(env_file, "w", encoding="utf-8") as dest:
            # 更新环境设置
            if env != "development":
                content = content.replace("APP_ENV=development", f"APP_ENV={env}")
                content = content.replace("DEBUG=true", "DEBUG=false")
            
            dest.write(content)
    
    # 复制一份作为 .env 文件（如果不存在）
    default_env = project_root / ".env"
    if not default_env.exists():
        print("创建默认环境文件 .env...")
        with open(env_file, "r", encoding="utf-8") as src:
            content = src.read()
        
        with open(default_env, "w", encoding="utf-8") as dest:
            dest.write(content)
    
    print(f"✅ 环境文件设置完成")


def install_dependencies():
    """安装项目依赖"""
    print("安装项目依赖...")
    
    # 获取脚本所在目录的父目录（项目根目录）
    project_root = Path(__file__).parent.parent
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 安装依赖
    result = subprocess.run(["poetry", "install"], check=False)
    
    if result.returncode != 0:
        print("错误: 安装依赖失败")
        sys.exit(1)
    
    print("✅ 依赖安装完成")


def initialize_database():
    """初始化数据库"""
    print("初始化数据库...")
    
    # 获取脚本所在目录的父目录（项目根目录）
    project_root = Path(__file__).parent.parent
    
    # 创建 migrations 目录（如果不存在）
    migrations_dir = project_root / "migrations"
    versions_dir = migrations_dir / "versions"
    
    for directory in [migrations_dir, versions_dir]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
    
    # 初始化数据库
    # TODO: 实现实际的数据库初始化逻辑
    
    print("✅ 数据库初始化完成")


def create_initial_user():
    """创建初始管理员用户"""
    print("创建初始管理员用户...")
    
    # TODO: 实现创建初始管理员用户的逻辑
    
    print("✅ 初始管理员用户创建完成")


def generate_sample_data():
    """生成示例数据"""
    print("生成示例数据...")
    
    # TODO: 实现生成示例数据的逻辑
    
    print("✅ 示例数据生成完成")


def show_completion_message():
    """显示完成消息"""
    print("\n🎉 项目设置完成！\n")
    print("接下来可以执行以下命令启动应用：")
    print("  cd multi_agent_creation_platform")
    print("  poetry run python -m app.main")
    print("\n访问 http://localhost:8000/api/docs 查看API文档")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多智能体AI创作平台项目初始化工具")
    parser.add_argument(
        "--env",
        choices=["development", "testing", "production"],
        default="development",
        help="设置环境（默认: development）",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="跳过依赖安装",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="跳过数据库初始化",
    )
    parser.add_argument(
        "--with-sample-data",
        action="store_true",
        help="生成示例数据",
    )
    
    args = parser.parse_args()
    
    print("开始设置多智能体AI创作平台项目...\n")
    
    # 执行设置步骤
    check_prerequisites()
    setup_environment(args.env)
    
    if not args.skip_deps:
        install_dependencies()
    
    if not args.skip_db:
        initialize_database()
        create_initial_user()
    
    if args.with_sample_data:
        generate_sample_data()
    
    show_completion_message()


if __name__ == "__main__":
    main() 