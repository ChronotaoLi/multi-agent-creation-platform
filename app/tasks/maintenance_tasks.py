"""
系统维护相关的异步任务模块

本模块实现系统维护、健康检查、清理过期数据等异步任务。
"""

import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import Task

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.utils.common_utils import get_utc_now

logger = logging.getLogger(__name__)
settings = get_settings()


class MaintenanceTaskBase(Task):
    """维护任务基类，包含通用的任务处理逻辑"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败处理"""
        logger.error(f"维护任务 {task_id} 失败: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=MaintenanceTaskBase,
    name="app.tasks.maintenance_tasks.system_health_check",
)
def system_health_check(self) -> Dict[str, Any]:
    """
    系统健康检查任务
    
    定期检查系统各组件的运行状态，包括数据库、缓存、消息队列等
    
    返回:
        检查结果
    """
    logger.info("开始系统健康检查")
    
    start_time = time.time()
    checks = {}
    
    try:
        # 检查数据库连接
        checks["database"] = check_database_connection()
        
        # 检查Redis连接
        checks["redis"] = check_redis_connection()
        
        # 检查Milvus连接
        checks["milvus"] = check_milvus_connection()
        
        # 检查消息队列连接
        checks["message_queue"] = check_message_queue_connection()
        
        # 检查存储
        checks["storage"] = check_storage()
        
        # 检查CPU和内存负载
        checks["system_resources"] = check_system_resources()
        
        # 整体状态判断
        overall_status = "healthy"
        for component, check_result in checks.items():
            if check_result["status"] != "ok":
                overall_status = "degraded"
                if check_result["status"] == "error":
                    # 如果有任何组件错误，系统状态为错误
                    overall_status = "error"
                    break
        
        # 准备结果
        result = {
            "timestamp": get_utc_now().isoformat(),
            "overall_status": overall_status,
            "checks": checks,
            "duration_ms": int((time.time() - start_time) * 1000),
        }
        
        # 如果系统状态异常，记录警告日志
        if overall_status != "healthy":
            failed_components = [
                component for component, check in checks.items() 
                if check["status"] != "ok"
            ]
            logger.warning(
                f"系统健康检查发现问题: 状态={overall_status}, 问题组件={failed_components}"
            )
            
            # 如果系统状态为错误，发送告警
            if overall_status == "error":
                # 延迟导入，避免循环依赖
                from app.tasks.notification_tasks import send_system_notification
                
                # 向管理员发送系统告警
                try:
                    admin_ids = get_admin_user_ids()
                    
                    for admin_id in admin_ids:
                        send_system_notification.delay(
                            user_id=admin_id,
                            notification_type="system.health_alert",
                            title=f"系统健康检查告警: {len(failed_components)}个组件异常",
                            message=f"系统健康检查发现以下组件异常: {', '.join(failed_components)}",
                            data={
                                "health_check": result,
                                "failed_components": failed_components,
                            },
                            priority="high",
                        )
                except Exception as e:
                    logger.error(f"发送系统健康告警通知失败: {str(e)}")
        
        logger.info(f"系统健康检查完成: status={overall_status}, duration={result['duration_ms']}ms")
        return result
        
    except Exception as e:
        logger.exception(f"系统健康检查时出错: {str(e)}")
        return {
            "timestamp": get_utc_now().isoformat(),
            "overall_status": "error",
            "error": str(e),
            "duration_ms": int((time.time() - start_time) * 1000),
        }


def check_database_connection() -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        # 延迟导入，避免循环依赖
        from sqlalchemy import text
        from app.data_access.repositories.base_repository import get_db
        
        start_time = time.time()
        db = next(get_db())
        result = db.execute(text("SELECT 1")).fetchone()
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "ok" if result and result[0] == 1 else "error",
            "latency_ms": latency_ms,
            "details": {"connected": True}
        }
    except Exception as e:
        logger.error(f"数据库连接检查失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "details": {"connected": False}
        }


def check_redis_connection() -> Dict[str, Any]:
    """检查Redis连接"""
    try:
        # 延迟导入，避免循环依赖
        from app.data_access.cache.redis_client import get_redis_client
        
        start_time = time.time()
        redis_client = get_redis_client()
        ping_result = redis_client.ping()
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 获取一些Redis信息
        info = redis_client.info()
        used_memory = info.get("used_memory_human", "unknown")
        clients = info.get("connected_clients", -1)
        
        return {
            "status": "ok" if ping_result else "error",
            "latency_ms": latency_ms,
            "details": {
                "connected": bool(ping_result),
                "used_memory": used_memory,
                "clients": clients,
            }
        }
    except Exception as e:
        logger.error(f"Redis连接检查失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "details": {"connected": False}
        }


def check_milvus_connection() -> Dict[str, Any]:
    """检查Milvus连接"""
    try:
        # 延迟导入，避免循环依赖
        from app.data_access.vector_store.milvus_client import get_milvus_client
        
        start_time = time.time()
        milvus_client = get_milvus_client()
        
        # 检查连接状态
        status = milvus_client.check_status()
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 获取一些Milvus信息
        collections = milvus_client.list_collections()
        
        return {
            "status": "ok" if status else "error",
            "latency_ms": latency_ms,
            "details": {
                "connected": bool(status),
                "collections_count": len(collections),
            }
        }
    except Exception as e:
        logger.error(f"Milvus连接检查失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "details": {"connected": False}
        }


def check_message_queue_connection() -> Dict[str, Any]:
    """检查消息队列连接"""
    try:
        # 延迟导入，避免循环依赖
        from celery.app.control import Control
        from app.core.celery_app import celery_app
        
        start_time = time.time()
        control = Control(celery_app)
        
        # 获取活动的worker
        workers = control.inspect().active()
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "ok" if workers else "warning",
            "latency_ms": latency_ms,
            "details": {
                "connected": workers is not None,
                "active_workers": len(workers or {}),
                "workers_info": list((workers or {}).keys()),
            }
        }
    except Exception as e:
        logger.error(f"消息队列连接检查失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "details": {"connected": False}
        }


def check_storage() -> Dict[str, Any]:
    """检查存储情况"""
    try:
        start_time = time.time()
        
        # 获取上传目录和临时目录的使用情况
        upload_dir = settings.UPLOAD_DIR
        temp_dir = settings.TEMP_DIR
        log_dir = settings.LOG_DIR
        
        upload_usage = get_directory_size(upload_dir)
        temp_usage = get_directory_size(temp_dir)
        log_usage = get_directory_size(log_dir)
        
        # 检查磁盘空间
        disk_usage = shutil.disk_usage(upload_dir)
        free_space_mb = disk_usage.free / (1024 * 1024)  # 转换为MB
        total_space_mb = disk_usage.total / (1024 * 1024)
        used_percent = (disk_usage.used / disk_usage.total) * 100
        
        # 根据可用空间判断状态
        status = "ok"
        if free_space_mb < 1024:  # 小于1GB时警告
            status = "warning"
        if free_space_mb < 512:   # 小于500MB时错误
            status = "error"
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": status,
            "latency_ms": latency_ms,
            "details": {
                "upload_dir_size_mb": round(upload_usage / (1024 * 1024), 2),
                "temp_dir_size_mb": round(temp_usage / (1024 * 1024), 2),
                "log_dir_size_mb": round(log_usage / (1024 * 1024), 2),
                "free_space_mb": round(free_space_mb, 2),
                "total_space_mb": round(total_space_mb, 2),
                "used_percent": round(used_percent, 2),
            }
        }
    except Exception as e:
        logger.error(f"存储检查失败: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "details": {}
        }


def check_system_resources() -> Dict[str, Any]:
    """检查系统资源使用情况"""
    try:
        start_time = time.time()
        
        import psutil
        
        # CPU负载
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 根据资源使用情况判断状态
        status = "ok"
        if cpu_percent > 80 or memory_percent > 80:  # 超过80%时警告
            status = "warning"
        if cpu_percent > 90 or memory_percent > 90:  # 超过90%时错误
            status = "error"
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": status,
            "latency_ms": latency_ms,
            "details": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_total_mb": round(memory.total / (1024 * 1024), 2),
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
            }
        }
    except Exception as e:
        logger.error(f"系统资源检查失败: {str(e)}")
        return {
            "status": "warning",  # 无法检查时警告而非错误
            "error": str(e),
            "details": {}
        }


def get_directory_size(path: str) -> int:
    """获取目录大小（字节）"""
    total_size = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    
    return total_size


def get_admin_user_ids() -> List[str]:
    """获取管理员用户ID列表"""
    # 实际项目中应该从数据库获取，这里简单返回配置中的管理员ID
    return settings.ADMIN_USER_IDS


@celery_app.task(
    bind=True,
    base=MaintenanceTaskBase,
    name="app.tasks.maintenance_tasks.cleanup_expired_sessions",
)
def cleanup_expired_sessions(self) -> Dict[str, Any]:
    """
    清理过期会话任务
    
    定期清理过期的用户会话记录
    
    返回:
        清理结果
    """
    try:
        logger.info("开始清理过期会话")
        
        # 延迟导入，避免循环依赖
        from app.services.auth_service import SessionService
        
        start_time = time.time()
        
        # 获取会话服务
        session_service = SessionService()
        
        # 清理过期会话
        cutoff_time = get_utc_now() - timedelta(days=settings.SESSION_EXPIRY_DAYS)
        deleted_count = session_service.delete_expired_sessions(cutoff_time)
        
        # 准备结果
        result = {
            "timestamp": get_utc_now().isoformat(),
            "deleted_count": deleted_count,
            "cutoff_time": cutoff_time.isoformat(),
            "duration_ms": int((time.time() - start_time) * 1000),
        }
        
        logger.info(f"过期会话清理完成: deleted={deleted_count}")
        return result
        
    except Exception as e:
        logger.exception(f"清理过期会话时出错: {str(e)}")
        return {
            "timestamp": get_utc_now().isoformat(),
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(
    bind=True,
    base=MaintenanceTaskBase,
    name="app.tasks.maintenance_tasks.cleanup_temporary_files",
)
def cleanup_temporary_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
    """
    清理临时文件任务
    
    定期清理超过指定时间的临时文件
    
    参数:
        max_age_hours: 文件保留的最大小时数
        
    返回:
        清理结果
    """
    try:
        logger.info(f"开始清理临时文件: max_age_hours={max_age_hours}")
        
        start_time = time.time()
        temp_dir = settings.TEMP_DIR
        cutoff_time = time.time() - (max_age_hours * 3600)  # 转换为秒
        
        if not os.path.exists(temp_dir):
            logger.warning(f"临时目录不存在: {temp_dir}")
            return {
                "timestamp": get_utc_now().isoformat(),
                "status": "skipped",
                "reason": "directory_not_exists",
                "path": temp_dir,
            }
        
        deleted_files = 0
        failed_files = 0
        saved_space = 0
        errors = []
        
        # 遍历临时目录
        for root, dirs, files in os.walk(temp_dir, topdown=True):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # 获取文件最后修改时间
                    file_mtime = os.path.getmtime(file_path)
                    
                    # 如果文件超过了最大保留时间
                    if file_mtime < cutoff_time:
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)
                        
                        # 删除文件
                        os.remove(file_path)
                        
                        deleted_files += 1
                        saved_space += file_size
                except Exception as e:
                    logger.error(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
                    failed_files += 1
                    errors.append({
                        "path": file_path,
                        "error": str(e),
                    })
        
        # 清理空目录
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for dir_name in dirs:
                try:
                    dir_path = os.path.join(root, dir_name)
                    if not os.listdir(dir_path):  # 如果目录为空
                        os.rmdir(dir_path)
                except Exception as e:
                    logger.error(f"删除空目录失败: {dir_path}, 错误: {str(e)}")
        
        # 准备结果
        result = {
            "timestamp": get_utc_now().isoformat(),
            "deleted_files": deleted_files,
            "failed_files": failed_files,
            "saved_space_mb": round(saved_space / (1024 * 1024), 2),
            "max_age_hours": max_age_hours,
            "duration_ms": int((time.time() - start_time) * 1000),
            "status": "completed",
        }
        
        if errors:
            result["errors"] = errors[:10]  # 最多返回10个错误
            if len(errors) > 10:
                result["errors_truncated"] = True
        
        logger.info(f"临时文件清理完成: deleted={deleted_files}, saved_space={result['saved_space_mb']}MB")
        return result
        
    except Exception as e:
        logger.exception(f"清理临时文件时出错: {str(e)}")
        return {
            "timestamp": get_utc_now().isoformat(),
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(
    bind=True,
    base=MaintenanceTaskBase,
    name="app.tasks.maintenance_tasks.rotate_logs",
)
def rotate_logs(self, max_log_age_days: int = 7) -> Dict[str, Any]:
    """
    轮转日志文件任务
    
    压缩和归档旧的日志文件，防止日志目录占用过多空间
    
    参数:
        max_log_age_days: 日志文件保留的最大天数
        
    返回:
        轮转结果
    """
    try:
        logger.info(f"开始轮转日志文件: max_age_days={max_log_age_days}")
        
        import gzip
        
        start_time = time.time()
        log_dir = settings.LOG_DIR
        cutoff_time = time.time() - (max_log_age_days * 86400)  # 转换为秒
        
        if not os.path.exists(log_dir):
            logger.warning(f"日志目录不存在: {log_dir}")
            return {
                "timestamp": get_utc_now().isoformat(),
                "status": "skipped",
                "reason": "directory_not_exists",
                "path": log_dir,
            }
        
        compressed_files = 0
        deleted_files = 0
        failed_files = 0
        errors = []
        
        # 遍历日志目录
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # 跳过已经压缩的文件
                    if file.endswith('.gz'):
                        # 检查压缩文件是否过期
                        file_mtime = os.path.getmtime(file_path)
                        if file_mtime < cutoff_time:
                            # 删除过期的压缩日志
                            os.remove(file_path)
                            deleted_files += 1
                        continue
                    
                    # 获取文件最后修改时间
                    file_mtime = os.path.getmtime(file_path)
                    
                    # 如果是旧的日志文件
                    if file_mtime < cutoff_time:
                        # 压缩日志文件
                        if file.endswith('.log'):
                            compressed_path = f"{file_path}.{int(file_mtime)}.gz"
                            with open(file_path, 'rb') as f_in:
                                with gzip.open(compressed_path, 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            
                            # 删除原文件
                            os.remove(file_path)
                            compressed_files += 1
                except Exception as e:
                    logger.error(f"处理日志文件失败: {file_path}, 错误: {str(e)}")
                    failed_files += 1
                    errors.append({
                        "path": file_path,
                        "error": str(e),
                    })
        
        # 准备结果
        result = {
            "timestamp": get_utc_now().isoformat(),
            "compressed_files": compressed_files,
            "deleted_files": deleted_files,
            "failed_files": failed_files,
            "max_age_days": max_log_age_days,
            "duration_ms": int((time.time() - start_time) * 1000),
            "status": "completed",
        }
        
        if errors:
            result["errors"] = errors[:10]  # 最多返回10个错误
            if len(errors) > 10:
                result["errors_truncated"] = True
        
        logger.info(f"日志轮转完成: compressed={compressed_files}, deleted={deleted_files}")
        return result
        
    except Exception as e:
        logger.exception(f"轮转日志文件时出错: {str(e)}")
        return {
            "timestamp": get_utc_now().isoformat(),
            "error": str(e),
            "status": "failed",
        }


@celery_app.task(
    bind=True,
    base=MaintenanceTaskBase,
    name="app.tasks.maintenance_tasks.backup_database",
)
def backup_database(self) -> Dict[str, Any]:
    """
    数据库备份任务
    
    创建数据库的备份，并可选地上传到远程存储
    
    返回:
        备份结果
    """
    try:
        logger.info("开始数据库备份")
        
        import subprocess
        from datetime import date
        
        start_time = time.time()
        backup_dir = settings.BACKUP_DIR
        
        # 确保备份目录存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 构建备份文件名
        today = date.today().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")
        backup_filename = f"db_backup_{today}_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 获取数据库连接信息
        db_host = settings.DATABASE_HOST
        db_port = settings.DATABASE_PORT
        db_name = settings.DATABASE_NAME
        db_user = settings.DATABASE_USER
        db_password = settings.DATABASE_PASSWORD
        
        # 构建pg_dump命令
        cmd = [
            "pg_dump",
            "-h", db_host,
            "-p", str(db_port),
            "-d", db_name,
            "-U", db_user,
            "-F", "c",  # 使用自定义格式
            "-f", backup_path
        ]
        
        # 设置环境变量以提供密码
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        # 执行备份命令
        process = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 检查命令执行结果
        if process.returncode != 0:
            error_msg = process.stderr.decode('utf-8')
            raise RuntimeError(f"数据库备份失败: {error_msg}")
        
        # 获取备份文件大小
        backup_size = os.path.getsize(backup_path)
        
        # 可选：压缩备份文件
        gzip_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(gzip_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 删除原始备份文件
        os.remove(backup_path)
        
        # 获取压缩文件大小
        compressed_size = os.path.getsize(gzip_path)
        
        # 可选：上传到远程存储（根据项目需要实现）
        
        # 准备结果
        result = {
            "timestamp": get_utc_now().isoformat(),
            "backup_file": gzip_path,
            "original_size_mb": round(backup_size / (1024 * 1024), 2),
            "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
            "compression_ratio": round((backup_size - compressed_size) / backup_size * 100, 2),
            "duration_ms": int((time.time() - start_time) * 1000),
            "status": "completed",
        }
        
        logger.info(f"数据库备份完成: file={gzip_path}, size={result['compressed_size_mb']}MB")
        return result
        
    except Exception as e:
        logger.exception(f"数据库备份时出错: {str(e)}")
        return {
            "timestamp": get_utc_now().isoformat(),
            "error": str(e),
            "status": "failed",
        }
