"""
WebSocket接口，用于实时通知和交互

提供WebSocket连接管理和各类通知端点
"""
import json
import logging
from typing import Dict, List, Optional, Union, Any, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, Cookie, Query, Depends, HTTPException, status
from fastapi.websockets import WebSocketState
from jose import JWTError, jwt

from app.core.config import get_settings
from app.data_access.event_bus.event_bus import EventBus, get_event_bus
from app.models.domain.user import User
from app.services.interfaces.project_service import ProjectService
from app.services.interfaces.user_service import UserService
from app.services.interfaces.workflow_service import WorkflowService
from app.api.v1.deps import (
    get_user_service, 
    get_project_service, 
    get_workflow_service,
    validate_project_access,
    validate_session_access
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器
    
    负责管理WebSocket连接和消息分发
    """
    
    def __init__(self):
        # 活跃连接映射: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 会话订阅映射: {session_id: {user_id: {connection_id}}}
        self.session_subscribers: Dict[str, Dict[str, Set[str]]] = {}
        # 项目订阅映射: {project_id: {user_id: {connection_id}}}
        self.project_subscribers: Dict[str, Dict[str, Set[str]]] = {}
        # 事件总线
        self.event_bus: Optional[EventBus] = None
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """建立WebSocket连接
        
        Args:
            websocket: WebSocket连接
            user_id: 用户ID
            
        Returns:
            str: 连接ID
        """
        await websocket.accept()
        
        # 生成唯一连接ID
        connection_id = str(uuid4())
        
        # 初始化用户连接字典
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        
        logger.info(f"WebSocket连接建立: user_id={user_id}, connection_id={connection_id}")
        
        return connection_id
    
    async def disconnect(self, user_id: str, connection_id: str) -> None:
        """断开WebSocket连接
        
        Args:
            user_id: 用户ID
            connection_id: 连接ID
        """
        # 从用户连接中移除
        if user_id in self.active_connections and connection_id in self.active_connections[user_id]:
            # 关闭连接前检查连接状态
            websocket = self.active_connections[user_id][connection_id]
            if websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"关闭WebSocket连接失败: {e}")
            
            # 移除连接
            del self.active_connections[user_id][connection_id]
            
            # 如果用户没有活跃连接，移除用户
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            logger.info(f"WebSocket连接断开: user_id={user_id}, connection_id={connection_id}")
        
        # 从会话订阅中移除
        for session_id, subscribers in self.session_subscribers.items():
            if user_id in subscribers and connection_id in subscribers[user_id]:
                subscribers[user_id].remove(connection_id)
                if not subscribers[user_id]:
                    del subscribers[user_id]
        
        # 从项目订阅中移除
        for project_id, subscribers in self.project_subscribers.items():
            if user_id in subscribers and connection_id in subscribers[user_id]:
                subscribers[user_id].remove(connection_id)
                if not subscribers[user_id]:
                    del subscribers[user_id]
    
    async def subscribe_to_session(self, session_id: str, user_id: str, connection_id: str) -> None:
        """订阅会话事件
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            connection_id: 连接ID
        """
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = {}
        
        if user_id not in self.session_subscribers[session_id]:
            self.session_subscribers[session_id][user_id] = set()
        
        self.session_subscribers[session_id][user_id].add(connection_id)
        logger.debug(f"已订阅会话: session_id={session_id}, user_id={user_id}, connection_id={connection_id}")
    
    async def subscribe_to_project(self, project_id: str, user_id: str, connection_id: str) -> None:
        """订阅项目事件
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            connection_id: 连接ID
        """
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = {}
        
        if user_id not in self.project_subscribers[project_id]:
            self.project_subscribers[project_id][user_id] = set()
        
        self.project_subscribers[project_id][user_id].add(connection_id)
        logger.debug(f"已订阅项目: project_id={project_id}, user_id={user_id}, connection_id={connection_id}")
    
    async def send_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """向用户发送消息
        
        Args:
            user_id: 用户ID
            message: 消息内容
        """
        if user_id in self.active_connections:
            disconnected = []
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"发送消息失败: {e}")
                    disconnected.append(connection_id)
            
            # 移除已断开的连接
            for connection_id in disconnected:
                await self.disconnect(user_id, connection_id)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """广播消息给所有用户
        
        Args:
            message: 消息内容
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_message(user_id, message)
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]) -> None:
        """广播消息给会话订阅者
        
        Args:
            session_id: 会话ID
            message: 消息内容
        """
        if session_id in self.session_subscribers:
            for user_id in list(self.session_subscribers[session_id].keys()):
                await self.send_message(user_id, message)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any]) -> None:
        """广播消息给项目订阅者
        
        Args:
            project_id: 项目ID
            message: 消息内容
        """
        if project_id in self.project_subscribers:
            for user_id in list(self.project_subscribers[project_id].keys()):
                await self.send_message(user_id, message)
    
    async def broadcast_to_users(self, user_ids: List[str], message: Dict[str, Any]) -> None:
        """广播消息给特定用户组
        
        Args:
            user_ids: 用户ID列表
            message: 消息内容
        """
        for user_id in user_ids:
            await self.send_message(user_id, message)
    
    def set_event_bus(self, event_bus: EventBus) -> None:
        """设置事件总线
        
        Args:
            event_bus: 事件总线实例
        """
        self.event_bus = event_bus


# 创建全局连接管理器实例
connection_manager = ConnectionManager()


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="访问令牌"),
    session_token: Optional[str] = Cookie(None, description="会话令牌")
) -> User:
    """WebSocket连接的用户身份验证
    
    Args:
        websocket: WebSocket实例
        token: 查询参数中的访问令牌
        session_token: Cookie中的会话令牌
        
    Returns:
        User: 验证通过的用户
        
    Raises:
        WebSocketException: 验证失败
    """
    settings = get_settings()
    user_service = get_user_service()
    
    # 获取令牌
    token_to_use = token or session_token
    if not token_to_use:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="未提供访问令牌")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="未提供访问令牌"
        )
    
    try:
        # 解码和验证JWT令牌
        payload = jwt.decode(
            token_to_use, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        # 检查令牌类型和过期时间
        token_type = payload.get("type")
        if token_type != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌类型")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="无效的令牌类型"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="无效的令牌"
            )
        
        # 从数据库获取用户
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="用户不存在"
            )
        
        # 检查用户状态
        if not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户未激活")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="用户未激活"
            )
        
        return user
        
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无效的令牌")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="无效的令牌"
        )


async def validate_project_access_ws(
    websocket: WebSocket,
    project_id: str,
    current_user: User = Depends(get_current_user_ws),
    project_service: ProjectService = Depends(get_project_service)
):
    """验证WebSocket连接中用户对项目的访问权限
    
    Args:
        websocket: WebSocket实例
        project_id: 项目ID
        current_user: 当前用户
        project_service: 项目服务
        
    Returns:
        Project: 项目信息
    """
    try:
        # 获取项目数据
        project = await project_service.get_project_by_id(project_id)
        if not project:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="项目不存在")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="项目不存在"
            )
        
        # 检查用户是否有访问权限
        if not await project_service.check_project_access(project_id, current_user.id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无权访问项目")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="无权访问项目"
            )
        
        return project
    
    except HTTPException:
        raise
    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="服务器内部错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"验证项目访问权限失败: {str(e)}"
        )


async def validate_session_access_ws(
    websocket: WebSocket,
    session_id: str,
    current_user: User = Depends(get_current_user_ws),
    workflow_service: WorkflowService = Depends(get_workflow_service)
):
    """验证WebSocket连接中用户对工作流会话的访问权限
    
    Args:
        websocket: WebSocket实例
        session_id: 会话ID
        current_user: 当前用户
        workflow_service: 工作流服务
        
    Returns:
        dict: 会话信息
    """
    try:
        # 获取会话状态
        session = await workflow_service.get_session_info(session_id)
        if not session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="会话不存在")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="会话不存在"
            )
        
        # 获取相关项目ID
        project_id = session.get("project_id")
        if not project_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="会话数据无效")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="会话数据无效"
            )
        
        # 检查项目访问权限
        project_service = get_project_service()
        if not await project_service.check_project_access(project_id, current_user.id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="无权访问会话")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="无权访问会话"
            )
        
        return session
    
    except HTTPException:
        raise
    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="服务器内部错误")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"验证会话访问权限失败: {str(e)}"
        )


async def handle_session_events(
    websocket: WebSocket, 
    session_id: str, 
    user_id: str, 
    connection_id: str
):
    """处理会话事件
    
    Args:
        websocket: WebSocket实例
        session_id: 会话ID
        user_id: 用户ID
        connection_id: 连接ID
    """
    event_bus = get_event_bus()
    if not event_bus:
        return
    
    # 异步方式订阅会话事件
    async def on_session_event(event_type: str, event_data: dict):
        if event_data.get("session_id") == session_id:
            # 转换为WebSocket消息格式
            message = {
                "type": event_type,
                "data": event_data
            }
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送会话事件失败: {e}")
                # 这里不需要断开连接，异常处理由外部函数处理
    
    # 订阅相关事件
    event_handlers = {
        "workflow.status_updated": on_session_event,
        "workflow.intervention_required": on_session_event,
        "workflow.content_updated": on_session_event,
        "workflow.error": on_session_event,
        "workflow.completed": on_session_event
    }
    
    # 注册事件处理器
    for event_type, handler in event_handlers.items():
        event_bus.subscribe(event_type, handler)
    
    # 发送初始状态
    workflow_service = get_workflow_service()
    try:
        status = await workflow_service.get_session_status(session_id)
        await websocket.send_json({
            "type": "initial_state",
            "data": status
        })
    except Exception as e:
        logger.error(f"获取会话状态失败: {e}")
    
    # 保持连接直到断开
    try:
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()
            # 解析客户端消息
            try:
                client_message = json.loads(data)
                message_type = client_message.get("type")
                
                # 处理心跳消息
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"无效的客户端消息: {data}")
    except WebSocketDisconnect:
        # 连接断开，清理资源
        for event_type, handler in event_handlers.items():
            event_bus.unsubscribe(event_type, handler)
    finally:
        # 确保移除连接
        await connection_manager.disconnect(user_id, connection_id)


async def handle_project_events(
    websocket: WebSocket, 
    project_id: str, 
    user_id: str, 
    connection_id: str
):
    """处理项目事件
    
    Args:
        websocket: WebSocket实例
        project_id: 项目ID
        user_id: 用户ID
        connection_id: 连接ID
    """
    event_bus = get_event_bus()
    if not event_bus:
        return
    
    # 异步方式订阅项目事件
    async def on_project_event(event_type: str, event_data: dict):
        if event_data.get("project_id") == project_id:
            # 转换为WebSocket消息格式
            message = {
                "type": event_type,
                "data": event_data
            }
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送项目事件失败: {e}")
    
    # 订阅相关事件
    event_handlers = {
        "project.updated": on_project_event,
        "content.created": on_project_event,
        "content.updated": on_project_event,
        "content.deleted": on_project_event,
        "agent.created": on_project_event,
        "agent.updated": on_project_event,
        "agent.deleted": on_project_event,
        "workflow.started": on_project_event,
        "workflow.completed": on_project_event
    }
    
    # 注册事件处理器
    for event_type, handler in event_handlers.items():
        event_bus.subscribe(event_type, handler)
    
    # 保持连接直到断开
    try:
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()
            # 解析客户端消息
            try:
                client_message = json.loads(data)
                message_type = client_message.get("type")
                
                # 处理心跳消息
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"无效的客户端消息: {data}")
    except WebSocketDisconnect:
        # 连接断开，清理资源
        for event_type, handler in event_handlers.items():
            event_bus.unsubscribe(event_type, handler)
    finally:
        # 确保移除连接
        await connection_manager.disconnect(user_id, connection_id)


async def handle_user_notifications(
    websocket: WebSocket, 
    user_id: str, 
    connection_id: str
):
    """处理用户通知
    
    Args:
        websocket: WebSocket实例
        user_id: 用户ID
        connection_id: 连接ID
    """
    event_bus = get_event_bus()
    if not event_bus:
        return
    
    # 异步方式订阅用户通知事件
    async def on_user_notification(event_type: str, event_data: dict):
        if event_data.get("user_id") == user_id:
            # 转换为WebSocket消息格式
            message = {
                "type": event_type,
                "data": event_data
            }
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送用户通知失败: {e}")
    
    # 订阅相关事件
    event_handlers = {
        "notification.system": on_user_notification,
        "notification.project_invite": on_user_notification,
        "notification.workflow_update": on_user_notification,
        "notification.content_update": on_user_notification
    }
    
    # 注册事件处理器
    for event_type, handler in event_handlers.items():
        event_bus.subscribe(event_type, handler)
    
    # 保持连接直到断开
    try:
        while True:
            # 等待客户端消息
            data = await websocket.receive_text()
            # 解析客户端消息
            try:
                client_message = json.loads(data)
                message_type = client_message.get("type")
                
                # 处理心跳消息
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                logger.warning(f"无效的客户端消息: {data}")
    except WebSocketDisconnect:
        # 连接断开，清理资源
        for event_type, handler in event_handlers.items():
            event_bus.unsubscribe(event_type, handler)
    finally:
        # 确保移除连接
        await connection_manager.disconnect(user_id, connection_id)


# WebSocket路由处理函数
# 这些函数需要在FastAPI应用实例中注册

async def sessions_endpoint(websocket: WebSocket, session_id: str):
    """会话通知端点
    
    Args:
        websocket: WebSocket实例
        session_id: 会话ID
    """
    # 验证用户身份
    try:
        user = await get_current_user_ws(websocket)
        # 验证会话访问权限
        await validate_session_access_ws(websocket, session_id)
        
        # 建立连接
        connection_id = await connection_manager.connect(websocket, str(user.id))
        
        # 订阅会话
        await connection_manager.subscribe_to_session(session_id, str(user.id), connection_id)
        
        # 处理会话事件
        await handle_session_events(websocket, session_id, str(user.id), connection_id)
    except HTTPException:
        # 验证失败，连接已在验证函数中关闭
        pass
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket会话处理错误: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def projects_endpoint(websocket: WebSocket, project_id: str):
    """项目通知端点
    
    Args:
        websocket: WebSocket实例
        project_id: 项目ID
    """
    # 验证用户身份
    try:
        user = await get_current_user_ws(websocket)
        # 验证项目访问权限
        await validate_project_access_ws(websocket, project_id)
        
        # 建立连接
        connection_id = await connection_manager.connect(websocket, str(user.id))
        
        # 订阅项目
        await connection_manager.subscribe_to_project(project_id, str(user.id), connection_id)
        
        # 处理项目事件
        await handle_project_events(websocket, project_id, str(user.id), connection_id)
    except HTTPException:
        # 验证失败，连接已在验证函数中关闭
        pass
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: project_id={project_id}")
    except Exception as e:
        logger.error(f"WebSocket项目处理错误: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def notifications_endpoint(websocket: WebSocket):
    """用户通知端点
    
    Args:
        websocket: WebSocket实例
    """
    # 验证用户身份
    try:
        user = await get_current_user_ws(websocket)
        
        # 建立连接
        connection_id = await connection_manager.connect(websocket, str(user.id))
        
        # 处理用户通知
        await handle_user_notifications(websocket, str(user.id), connection_id)
    except HTTPException:
        # 验证失败，连接已在验证函数中关闭
        pass
    except WebSocketDisconnect:
        logger.info(f"用户通知WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket用户通知处理错误: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


def register_websocket_routes(app):
    """注册WebSocket路由
    
    Args:
        app: FastAPI应用实例
    """
    app.websocket("/ws/sessions/{session_id}")(sessions_endpoint)
    app.websocket("/ws/projects/{project_id}")(projects_endpoint)
    app.websocket("/ws/notifications")(notifications_endpoint)
    
    # 设置事件总线
    event_bus = get_event_bus()
    connection_manager.set_event_bus(event_bus)
