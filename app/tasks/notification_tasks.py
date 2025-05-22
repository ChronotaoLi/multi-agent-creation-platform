"""
通知相关的异步任务模块

本模块实现邮件通知、WebSocket推送、系统消息等异步通知任务。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery import Task

from app.core.celery_app import celery_app
from app.utils.common_utils import get_utc_now

logger = logging.getLogger(__name__)


class NotificationTaskBase(Task):
    """通知任务基类，包含通用的任务处理逻辑"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败处理"""
        logger.error(f"通知任务 {task_id} 失败: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.send_email_notification",
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notification(
    self, 
    recipient_email: str, 
    subject: str,
    template_name: str,
    template_params: Dict[str, Any],
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    priority: str = "normal",
) -> Dict[str, Any]:
    """
    发送邮件通知的异步任务
    
    参数:
        recipient_email: 收件人邮箱
        subject: 邮件主题
        template_name: 邮件模板名称
        template_params: 邮件模板参数
        cc: 抄送列表
        bcc: 密送列表
        priority: 优先级（high, normal, low）
        
    返回:
        发送结果
    """
    try:
        logger.info(f"开始发送邮件通知: recipient={recipient_email}, subject={subject}")
        
        # 延迟导入，避免循环依赖
        from app.services.notification_service import EmailService
        
        # 创建邮件服务
        email_service = EmailService()
        
        # 发送邮件
        message_id = email_service.send_template_email(
            recipient=recipient_email,
            subject=subject,
            template_name=template_name,
            template_params=template_params,
            cc=cc or [],
            bcc=bcc or [],
            priority=priority,
        )
        
        # 准备结果数据
        result = {
            "message_id": message_id,
            "recipient": recipient_email,
            "subject": subject,
            "template": template_name,
            "sent_at": get_utc_now().isoformat(),
            "status": "sent",
        }
        
        logger.info(f"邮件通知发送完成: recipient={recipient_email}, message_id={message_id}")
        return result
    
    except Exception as e:
        logger.exception(f"发送邮件通知时出错: {str(e)}")
        # 重试任务，指数退避策略
        self.retry(exc=e, countdown=min(60 * 2 ** self.request.retries, 60 * 60))


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.send_bulk_email_notifications",
    max_retries=2,
    default_retry_delay=120,
)
def send_bulk_email_notifications(
    self, 
    recipients: List[Dict[str, Any]],
    subject_template: str,
    template_name: str,
    global_template_params: Optional[Dict[str, Any]] = None,
    priority: str = "normal",
) -> Dict[str, Any]:
    """
    批量发送邮件通知的异步任务
    
    参数:
        recipients: 收件人列表，每项包含email和template_params
        subject_template: 邮件主题模板
        template_name: 邮件模板名称
        global_template_params: 全局模板参数
        priority: 优先级（high, normal, low）
        
    返回:
        发送结果
    """
    try:
        recipient_count = len(recipients)
        logger.info(f"开始批量发送邮件通知: recipients={recipient_count}")
        
        # 确保全局参数是字典
        if global_template_params is None:
            global_template_params = {}
        
        # 延迟导入，避免循环依赖
        from app.services.notification_service import EmailService
        from app.utils.template_utils import render_string_template
        
        # 创建邮件服务
        email_service = EmailService()
        
        # 结果统计
        results = {
            "total": recipient_count,
            "successful": 0,
            "failed": 0,
            "details": [],
        }
        
        # 为每位收件人发送邮件
        for recipient_data in recipients:
            try:
                email = recipient_data.get("email")
                # 合并全局参数和收件人特定参数
                template_params = {**global_template_params, **recipient_data.get("template_params", {})}
                
                # 渲染主题
                subject = render_string_template(subject_template, template_params)
                
                # 发送邮件
                message_id = email_service.send_template_email(
                    recipient=email,
                    subject=subject,
                    template_name=template_name,
                    template_params=template_params,
                    priority=priority,
                )
                
                results["successful"] += 1
                results["details"].append({
                    "email": email,
                    "status": "sent",
                    "message_id": message_id,
                })
                
            except Exception as e:
                logger.error(f"发送邮件到 {recipient_data.get('email')} 失败: {str(e)}")
                results["failed"] += 1
                results["details"].append({
                    "email": recipient_data.get("email", "unknown"),
                    "status": "failed",
                    "error": str(e),
                })
        
        # 添加结果汇总
        results["completed_at"] = get_utc_now().isoformat()
        
        logger.info(f"批量邮件通知发送完成: 成功={results['successful']}, 失败={results['failed']}")
        return results
    
    except Exception as e:
        logger.exception(f"批量发送邮件通知时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.send_system_notification",
    max_retries=2,
    default_retry_delay=30,
)
def send_system_notification(
    self, 
    user_id: str, 
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    priority: str = "normal",
    expiration: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    发送系统通知的异步任务
    
    参数:
        user_id: 用户ID
        notification_type: 通知类型
        title: 通知标题
        message: 通知内容
        data: 附加数据
        priority: 优先级（high, normal, low）
        expiration: 过期时间
        
    返回:
        通知结果
    """
    try:
        logger.info(f"开始发送系统通知: user_id={user_id}, type={notification_type}, title={title}")
        
        # 延迟导入，避免循环依赖
        from app.services.notification_service import SystemNotificationService
        
        # 创建系统通知服务
        notification_service = SystemNotificationService()
        
        # 发送系统通知
        notification_id = notification_service.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            priority=priority,
            expiration=expiration,
        )
        
        # 准备结果数据
        result = {
            "notification_id": notification_id,
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "sent_at": get_utc_now().isoformat(),
            "status": "sent",
        }
        
        logger.info(f"系统通知发送完成: user_id={user_id}, notification_id={notification_id}")
        return result
    
    except Exception as e:
        logger.exception(f"发送系统通知时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.send_batch_system_notifications",
    max_retries=2,
)
def send_batch_system_notifications(
    self, 
    user_ids: List[str], 
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    priority: str = "normal",
    expiration: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    批量发送系统通知的异步任务
    
    参数:
        user_ids: 用户ID列表
        notification_type: 通知类型
        title: 通知标题
        message: 通知内容
        data: 附加数据
        priority: 优先级（high, normal, low）
        expiration: 过期时间
        
    返回:
        通知结果
    """
    try:
        user_count = len(user_ids)
        logger.info(f"开始批量发送系统通知: users={user_count}, type={notification_type}, title={title}")
        
        # 延迟导入，避免循环依赖
        from app.services.notification_service import SystemNotificationService
        
        # 创建系统通知服务
        notification_service = SystemNotificationService()
        
        # 结果统计
        results = {
            "total": user_count,
            "successful": 0,
            "failed": 0,
            "notification_ids": [],
        }
        
        # 批量创建通知
        notification_ids = notification_service.batch_create_notifications(
            user_ids=user_ids,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            priority=priority,
            expiration=expiration,
        )
        
        results["successful"] = len(notification_ids)
        results["failed"] = user_count - len(notification_ids)
        results["notification_ids"] = notification_ids
        
        # 添加结果汇总
        results["completed_at"] = get_utc_now().isoformat()
        
        logger.info(f"批量系统通知发送完成: 成功={results['successful']}, 失败={results['failed']}")
        return results
    
    except Exception as e:
        logger.exception(f"批量发送系统通知时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.push_websocket_notification",
    max_retries=3,
    default_retry_delay=15,
)
def push_websocket_notification(
    self, 
    event_type: str,
    data: Dict[str, Any],
    user_ids: Optional[List[str]] = None,
    session_ids: Optional[List[str]] = None,
    groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    推送WebSocket通知的异步任务
    
    参数:
        event_type: 事件类型
        data: 事件数据
        user_ids: 指定用户ID列表
        session_ids: 指定会话ID列表
        groups: 指定组列表
        
    返回:
        推送结果
    """
    try:
        target_count = sum([
            len(user_ids or []),
            len(session_ids or []),
            len(groups or [])
        ])
        logger.info(f"开始推送WebSocket通知: event_type={event_type}, targets={target_count}")
        
        # 延迟导入，避免循环依赖
        from app.services.websocket_service import WebSocketManager
        
        # 获取WebSocket管理器
        ws_manager = WebSocketManager.get_instance()
        
        # 准备事件数据
        event_data = {
            "type": event_type,
            "timestamp": get_utc_now().isoformat(),
            "data": data,
        }
        
        # 分别推送到不同目标
        sent_count = 0
        
        if user_ids:
            user_sent = ws_manager.broadcast_to_users(user_ids, event_data)
            sent_count += user_sent
            
        if session_ids:
            session_sent = ws_manager.broadcast_to_sessions(session_ids, event_data)
            sent_count += session_sent
            
        if groups:
            group_sent = ws_manager.broadcast_to_groups(groups, event_data)
            sent_count += group_sent
        
        # 准备结果数据
        result = {
            "event_type": event_type,
            "targets": {
                "users": len(user_ids or []),
                "sessions": len(session_ids or []),
                "groups": len(groups or []),
            },
            "sent_count": sent_count,
            "sent_at": get_utc_now().isoformat(),
            "status": "sent" if sent_count > 0 else "no_recipients",
        }
        
        logger.info(f"WebSocket通知推送完成: event_type={event_type}, sent={sent_count}")
        return result
    
    except Exception as e:
        logger.exception(f"推送WebSocket通知时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=NotificationTaskBase,
    name="app.tasks.notification_tasks.send_project_update_notification",
    max_retries=2,
)
def send_project_update_notification(
    self, 
    project_id: str,
    project_name: str,
    update_type: str,
    update_summary: str,
    update_details: Dict[str, Any],
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    发送项目更新通知的异步任务
    
    参数:
        project_id: 项目ID
        project_name: 项目名称
        update_type: 更新类型
        update_summary: 更新摘要
        update_details: 更新详情
        actor_id: 操作者ID
        
    返回:
        通知结果
    """
    try:
        logger.info(f"开始发送项目更新通知: project_id={project_id}, update_type={update_type}")
        
        # 延迟导入，避免循环依赖
        from app.services.project_service import ProjectService
        from app.services.notification_service import SystemNotificationService
        
        # 创建项目服务
        project_service = ProjectService()
        notification_service = SystemNotificationService()
        
        # 获取项目成员ID列表
        member_ids = project_service.get_project_member_ids(project_id)
        
        if not member_ids:
            logger.warning(f"项目 {project_id} 没有可通知的成员")
            return {
                "project_id": project_id,
                "status": "skipped",
                "reason": "no_members",
                "timestamp": get_utc_now().isoformat(),
            }
        
        # 生成通知标题和内容
        title = f"{project_name}: {update_summary}"
        message = self._format_update_message(update_type, update_summary, update_details)
        
        # 构建附加数据
        data = {
            "project_id": project_id,
            "project_name": project_name,
            "update_type": update_type,
            "update_details": update_details,
            "actor_id": actor_id,
        }
        
        # 批量发送系统通知
        notification_ids = notification_service.batch_create_notifications(
            user_ids=member_ids,
            notification_type=f"project.{update_type}",
            title=title,
            message=message,
            data=data,
        )
        
        # 同时通过WebSocket推送
        push_websocket_notification.delay(
            event_type="project_update",
            data={
                "project_id": project_id,
                "project_name": project_name,
                "update_type": update_type,
                "update_summary": update_summary,
                "timestamp": get_utc_now().isoformat(),
                "actor_id": actor_id,
            },
            user_ids=member_ids,
        )
        
        # 准备结果数据
        result = {
            "project_id": project_id,
            "update_type": update_type,
            "notification_count": len(notification_ids),
            "notification_ids": notification_ids,
            "sent_at": get_utc_now().isoformat(),
            "status": "sent",
        }
        
        logger.info(f"项目更新通知发送完成: project_id={project_id}, notifications={len(notification_ids)}")
        return result
    
    except Exception as e:
        logger.exception(f"发送项目更新通知时出错: {str(e)}")
        # 重试任务
        self.retry(exc=e)
    
    def _format_update_message(self, update_type: str, summary: str, details: Dict[str, Any]) -> str:
        """格式化更新消息内容"""
        if update_type == "content_created":
            return f"{summary}\n\n类型: {details.get('content_type', '未知')}\n创建者: {details.get('creator_name', '系统')}"
        
        elif update_type == "workflow_completed":
            return f"{summary}\n\n工作流: {details.get('workflow_name', '未知')}\n状态: {details.get('status', '完成')}"
        
        elif update_type == "member_added":
            return f"{summary}\n\n新成员: {details.get('user_name', '未知')}\n角色: {details.get('role', '成员')}"
        
        elif update_type == "comment_added":
            return f"{summary}\n\n评论者: {details.get('user_name', '未知')}\n内容: {details.get('comment_text', '')[:100]}"
        
        # 默认格式
        return summary
