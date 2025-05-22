"""
工作流API集成测试模块

测试工作流相关API端点：获取工作流类型、启动工作流、查询会话状态、处理用户干预等
"""
import pytest
from unittest.mock import patch, AsyncMock, ANY
import json
from fastapi.testclient import TestClient
import uuid

from app.models.schemas import (
    WorkflowSession,
    WorkflowSessionStatus,
    WorkflowStartConfig,
    InterventionData,
    InterventionResult
)


class TestWorkflowsAPI:
    """工作流API测试类"""
    
    def test_get_workflow_types(self, client, mocker):
        """测试获取工作流类型列表"""
        # 模拟服务层返回的工作流类型列表
        mock_types = [
            {
                "id": "free",
                "name": "自由创作",
                "description": "自由创作模式",
                "capabilities": ["故事创作", "角色设计"],
                "config_schema": {}
            },
            {
                "id": "guided",
                "name": "引导式创作",
                "description": "引导式创作模式",
                "capabilities": ["故事创作", "情节构建"],
                "config_schema": {}
            }
        ]
        
        # 打补丁模拟服务层调用
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(get_workflow_types=AsyncMock(return_value=mock_types))
        )
        
        # 发送请求（加上认证头）
        response = client.get("/workflows/types", headers={"Authorization": "Bearer test_token"})
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert len(data) == 2
        assert data[0]["id"] == "free"
        assert data[1]["id"] == "guided"
        
        # 验证字段完整性
        expected_fields = ["id", "name", "description", "capabilities", "config_schema"]
        for field in expected_fields:
            assert field in data[0]
            assert field in data[1]
    
    def test_start_workflow_success(self, client, mocker):
        """测试成功启动工作流"""
        # 准备测试数据
        request_data = {
            "workflow_type": "free",
            "project_id": 123,
            "initial_data": {"theme": "fantasy"},
            "agents": [1, 2]
        }
        
        # 获取固定的会话ID (用于模拟客户端)
        fixed_session_id = "954f8b0d-f98e-4830-b252-7dd936b2bc2f"
        
        # 模拟服务层返回的会话状态
        mock_session = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 123,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "planning",
            "messages": [{"role": "system", "content": "开始创作过程"}],
            "next_steps": ["继续", "修改"],
            "start_time": "2025-05-21T10:00:00",
            "update_time": "2025-05-21T10:00:00"
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(start_workflow=AsyncMock(return_value=mock_session))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.post(
            "/workflows/start",
            json=request_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 201
        data = response.json()
        
        # 验证返回的数据
        assert data["session_id"] == mock_session["session_id"]
        assert data["workflow_type"] == request_data["workflow_type"]
        assert data["project_id"] == request_data["project_id"]
        assert data["status"] == "in_progress"
        assert "messages" in data
        assert "next_steps" in data
    
    def test_start_workflow_missing_token(self, client, mocker):
        """测试启动工作流失败 - 缺少令牌"""
        # 准备测试数据
        request_data = {
            "workflow_type": "free",
            "project_id": 123,
            "initial_data": {"theme": "fantasy"},
            "agents": [1, 2]
        }
        
        # 发送请求（不包含认证头）
        response = client.post("/workflows/start", json=request_data)
        
        # 验证响应 - 应该是401未授权
        assert response.status_code == 401
    
    def test_get_session_status_success(self, client, mocker):
        """测试成功获取会话状态"""
        # 准备测试数据
        fixed_session_id = "954f8b0d-f98e-4830-b252-7dd936b2bc2f"
        
        # 模拟服务层返回的会话状态
        mock_status = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 123,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "writing",
            "messages": [
                {"role": "system", "content": "开始创作过程"},
                {"role": "assistant", "content": "我们来开始创作故事"}
            ],
            "next_steps": ["继续", "修改", "完成"],
            "start_time": "2025-05-21T10:00:00",
            "update_time": "2025-05-21T10:05:00"
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(get_session_status=AsyncMock(return_value=mock_status))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.get(
            f"/workflows/sessions/{fixed_session_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert data["session_id"] == mock_status["session_id"]
        assert data["workflow_type"] == mock_status["workflow_type"]
        assert data["project_id"] == mock_status["project_id"]
        assert data["status"] == mock_status["status"]
        assert data["current_stage"] == mock_status["current_stage"]
        assert len(data["messages"]) == len(mock_status["messages"])
    
    def test_get_session_status_not_found(self, client, mocker):
        """测试获取会话状态失败 - 会话不存在"""
        # 准备测试数据
        session_id = "not_found_session_id"
        
        # 打补丁模拟服务层调用和用户认证
        mock_service = AsyncMock()
        mock_service.get_session_status = AsyncMock(side_effect=ValueError("会话不存在"))
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=mock_service
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.get(
            f"/workflows/sessions/{session_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应 - 应该是404未找到
        assert response.status_code == 404
        data = response.json()
        
        # 验证错误消息
        assert "detail" in data
        assert "会话不存在" in data["detail"] or "not found" in data["detail"].lower()
    
    def test_process_intervention_success(self, client, mocker):
        """测试成功处理用户干预"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        intervention_data = {
            "intervention_type": "content_edit",
            "content": {"text": "修改后的内容"},
            "target_stage": "writing"
        }
        
        # 模拟服务层返回的处理结果
        mock_result = {
            "success": True,
            "message": "成功处理干预请求",
            "status": {
                "session_id": session_id,
                "workflow_type": "free",
                "project_id": 123,
                "user_id": 1,
                "status": "in_progress",
                "current_stage": "writing",
                "messages": [
                    {"role": "assistant", "content": "请编辑内容"},
                    {"role": "user", "content": "修改后的内容"},
                    {"role": "assistant", "content": "内容已更新"}
                ],
                "next_steps": ["继续", "完成"],
                "start_time": "2025-05-21T10:00:00",
                "update_time": "2025-05-21T10:10:00"
            }
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(process_intervention=AsyncMock(return_value=mock_result))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.post(
            f"/workflows/sessions/{session_id}/intervention",
            json=intervention_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert data["success"] is True
        assert "成功处理干预" in data["message"]
        assert data["status"]["session_id"] == session_id
        assert data["status"]["status"] == "in_progress"
        assert data["status"]["current_stage"] == "writing"
        assert len(data["status"]["messages"]) == 3
        assert data["status"]["next_steps"] == ["继续", "完成"]
    
    def test_pause_session_success(self, client, mocker):
        """测试成功暂停会话"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        
        # 模拟服务层返回的会话状态
        mock_status = {
            "session_id": session_id,
            "workflow_type": "free",
            "project_id": 123,
            "user_id": 1,
            "status": "paused",
            "current_stage": "writing",
            "messages": [
                {"role": "system", "content": "会话已暂停"}
            ],
            "next_steps": [],
            "start_time": "2025-05-21T10:00:00",
            "update_time": "2025-05-21T10:15:00"
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(pause_session=AsyncMock(return_value=mock_status))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.post(
            f"/workflows/sessions/{session_id}/pause",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert data["session_id"] == session_id
        assert data["status"] == "paused"  # 状态已更改为暂停
    
    def test_resume_session_success(self, client, mocker):
        """测试成功恢复会话"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        
        # 模拟服务层返回的会话状态
        mock_status = {
            "session_id": session_id,
            "workflow_type": "free",
            "project_id": 123,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "writing",
            "messages": [
                {"role": "system", "content": "会话已恢复"}
            ],
            "next_steps": ["继续", "修改"],
            "start_time": "2025-05-21T10:00:00",
            "update_time": "2025-05-21T10:20:00"
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(resume_session=AsyncMock(return_value=mock_status))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.post(
            f"/workflows/sessions/{session_id}/resume",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert data["session_id"] == session_id
        assert data["status"] == "in_progress"  # 状态已更改为运行中
        assert data["current_stage"] == "writing"
    
    def test_cancel_session_success(self, client, mocker):
        """测试成功取消会话"""
        # 准备测试数据
        session_id = str(uuid.uuid4())
        
        # 模拟服务层返回的会话状态
        mock_status = {
            "session_id": session_id,
            "workflow_type": "free",
            "project_id": 123,
            "user_id": 1,
            "status": "cancelled",
            "current_stage": "writing",
            "messages": [
                {"role": "system", "content": "会话已取消"}
            ],
            "next_steps": [],
            "start_time": "2025-05-21T10:00:00",
            "update_time": "2025-05-21T10:25:00"
        }
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(cancel_session=AsyncMock(return_value=mock_status))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": 1, "username": "testuser"}
        )
        
        # 发送请求
        response = client.post(
            f"/workflows/sessions/{session_id}/cancel",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert data["session_id"] == session_id
        assert data["status"] == "cancelled"  # 状态已更改为取消
    
    def test_list_user_sessions_success(self, client, mocker):
        """测试成功获取用户会话列表"""
        # 准备测试数据
        user_id = 1
        
        # 模拟服务层返回的会话列表
        mock_sessions = [
            {
                "session_id": str(uuid.uuid4()),
                "workflow_type": "free",
                "project_id": 123,
                "user_id": user_id,
                "status": "in_progress",
                "current_stage": "writing",
                "start_time": "2025-05-21T10:00:00",
                "update_time": "2025-05-21T10:20:00"
            },
            {
                "session_id": str(uuid.uuid4()),
                "workflow_type": "guided",
                "project_id": 456,
                "user_id": user_id,
                "status": "paused",
                "current_stage": "planning",
                "start_time": "2025-05-20T15:00:00",
                "update_time": "2025-05-20T15:30:00"
            }
        ]
        
        # 打补丁模拟服务层调用和用户认证
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=AsyncMock(list_user_sessions=AsyncMock(return_value=mock_sessions))
        )
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value={"id": user_id, "username": "testuser"}
        )
        
        # 发送请求
        response = client.get(
            "/workflows/sessions",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的数据
        assert len(data) == 2
        assert data[0]["user_id"] == user_id
        assert data[1]["user_id"] == user_id 