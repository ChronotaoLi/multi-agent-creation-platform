"""
创作工作流端到端测试模块

测试完整的创作工作流程场景，从启动工作流到最终完成，包括中间的用户干预和状态变化
"""
import pytest
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.schemas import (
    WorkflowStartConfig,
    WorkflowSessionStatus,
    InterventionData
)


class TestCreationWorkflow:
    """创作工作流端到端测试类"""
    
    @pytest.mark.asyncio
    async def test_complete_creative_workflow(self, client, mocker):
        """测试完整的创作工作流程"""
        # ======== 步骤1：启动工作流 ========
        # 模拟用户身份
        user_data = {"id": 1, "username": "testuser"}
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_current_user",
            return_value=user_data
        )
        
        # 固定的会话ID
        fixed_session_id = "954f8b0d-f98e-4830-b252-7dd936b2bc2f"
        
        # 准备工作流启动配置
        start_config = {
            "workflow_type": "free",
            "project_id": 101,
            "initial_data": {"theme": "科幻冒险", "setting": "未来太空殖民地"},
            "agents": [1, 2, 3]  # 假设这些是不同专家智能体的ID
        }
        
        # 模拟工作流服务返回初始状态
        initial_status = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 101,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "planning",
            "messages": [
                {"role": "system", "content": "创作工作流已启动"},
                {"role": "assistant", "content": "我们将开始创建一个科幻冒险故事，设定在未来太空殖民地。"}
            ],
            "next_steps": ["继续规划", "添加角色"],
            "start_time": datetime.now().isoformat(),
            "update_time": datetime.now().isoformat()
        }
        
        # 打补丁模拟服务层调用
        mock_workflow_service = AsyncMock()
        mock_workflow_service.start_workflow.return_value = initial_status
        mocker.patch(
            "app.api.v1.endpoints.workflows.get_workflow_service",
            return_value=mock_workflow_service
        )
        
        # 发送启动请求
        response = client.post(
            "/workflows/start",
            json=start_config,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == initial_status["session_id"]
        assert data["workflow_type"] == start_config["workflow_type"]
        assert data["project_id"] == start_config["project_id"]
        
        # ======== 步骤2：发送用户干预 ========
        # 假设用户想要添加一个角色
        intervention_data = {
            "intervention_type": "add_character",
            "content": {
                "name": "艾丽卡",
                "role": "宇航员",
                "background": "前军事飞行员，现在是殖民地的首席勘探官。"
            }
        }
        
        # 模拟处理干预后的会话状态
        updated_status = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 101,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "character_design",
            "messages": [
                # 以前的消息
                {"role": "system", "content": "创作工作流已启动"},
                {"role": "assistant", "content": "我们将开始创建一个科幻冒险故事，设定在未来太空殖民地。"},
                # 新的干预消息
                {"role": "user", "content": "添加角色：艾丽卡，宇航员，前军事飞行员，现在是殖民地的首席勘探官。"},
                {"role": "assistant", "content": "已添加角色艾丽卡。她作为前军事飞行员的背景将为故事增添紧张感和专业知识。"}
            ],
            "next_steps": ["继续设计角色", "开始情节构建"],
            "start_time": initial_status["start_time"],
            "update_time": datetime.now().isoformat()
        }
        
        # 模拟干预处理服务
        mock_workflow_service.process_intervention.return_value = {
            "success": True,
            "message": "成功添加角色",
            "status": updated_status
        }
        
        # 发送干预请求
        response = client.post(
            f"/workflows/sessions/{fixed_session_id}/intervention",
            json=intervention_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data
        assert data["status"]["session_id"] == fixed_session_id
        assert data["status"]["current_stage"] == "character_design"
        assert len(data["status"]["messages"]) > len(initial_status["messages"])
        
        # ======== 步骤3：暂停工作流 ========
        # 模拟暂停后的会话状态
        paused_status = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 101,
            "user_id": 1,
            "status": "paused",
            "current_stage": "character_design",
            "messages": updated_status["messages"] + [
                {"role": "system", "content": "会话已暂停"}
            ],
            "next_steps": [],
            "start_time": initial_status["start_time"],
            "update_time": datetime.now().isoformat()
        }
        
        # 模拟暂停服务
        mock_workflow_service.pause_session.return_value = paused_status
        
        # 发送暂停请求
        response = client.post(
            f"/workflows/sessions/{fixed_session_id}/pause",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["session_id"] == fixed_session_id
        
        # ======== 步骤4：恢复工作流 ========
        # 模拟恢复后的会话状态
        resumed_status = {
            "session_id": fixed_session_id,
            "workflow_type": "free",
            "project_id": 101,
            "user_id": 1,
            "status": "in_progress",
            "current_stage": "character_design",
            "messages": paused_status["messages"] + [
                {"role": "system", "content": "会话已恢复"}
            ],
            "next_steps": ["继续设计角色", "开始情节构建"],
            "start_time": initial_status["start_time"],
            "update_time": datetime.now().isoformat()
        }
        
        # 模拟恢复服务
        mock_workflow_service.resume_session.return_value = resumed_status
        
        # 发送恢复请求
        response = client.post(
            f"/workflows/sessions/{fixed_session_id}/resume",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["session_id"] == fixed_session_id
        
        # ======== 步骤5：完成工作流 ========
        # 模拟工作流最终内容输出
        final_content = {
            "title": "太空殖民地的秘密",
            "synopsis": "在太空殖民地内，首席勘探官艾丽卡发现了一个可能改变人类命运的神秘信号...",
            "characters": [
                {
                    "name": "艾丽卡",
                    "role": "宇航员",
                    "background": "前军事飞行员，现在是殖民地的首席勘探官。"
                },
                {
                    "name": "莱昂",
                    "role": "科学家",
                    "background": "天体生物学家，专注于寻找外星生命。"
                }
            ],
            "plot_points": [
                "艾丽卡在例行勘测中发现神秘信号",
                "莱昂分析信号发现它可能是外星文明的通讯",
                "殖民地高层试图隐瞒这一发现",
                "艾丽卡和莱昂合作调查真相"
            ]
        }
        
        # 模拟完成工作流
        mock_workflow_service.complete_workflow = AsyncMock(return_value={
            "success": True,
            "message": "创作工作流程已完成",
            "content": final_content,
            "session_id": fixed_session_id
        })
        
        # 发送完成请求
        response = client.post(
            f"/workflows/sessions/{fixed_session_id}/complete",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data
        assert data["content"]["title"] == "太空殖民地的秘密"
        assert len(data["content"]["characters"]) == 2
        assert len(data["content"]["plot_points"]) == 4
        
        # ======== 步骤6：尝试干预已完成的工作流 - 应该失败 ========
        # 准备干预数据
        invalid_intervention = {
            "intervention_type": "content_edit",
            "content": {"text": "尝试修改已完成的内容"},
            "target_stage": "writing"
        }
        
        # 模拟错误响应
        mock_workflow_service.process_intervention.side_effect = ValueError("无法干预已完成的工作流")
        
        # 发送干预请求
        response = client.post(
            f"/workflows/sessions/{fixed_session_id}/intervention",
            json=invalid_intervention,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应 - 应该是400错误
        assert response.status_code == 400
        data = response.json()
        assert "无法干预已完成的工作流" in data.get("detail", "")
        
        # ======== 步骤7：获取用户会话列表 ========
        # 模拟用户会话列表
        mock_sessions = [
            {
                "session_id": fixed_session_id,
                "workflow_type": "free",
                "project_id": 101,
                "user_id": 1,
                "status": "completed",
                "current_stage": "completed",
                "start_time": datetime.now().isoformat(),
                "update_time": (datetime.now() + timedelta(minutes=6)).isoformat()
            },
            {
                "session_id": str(uuid.uuid4()),
                "workflow_type": "guided",
                "project_id": 102,
                "user_id": 1,
                "status": "paused",
                "current_stage": "planning",
                "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "update_time": (datetime.now() - timedelta(days=1, minutes=-30)).isoformat()
            }
        ]
        
        # 更新模拟返回值
        mock_workflow_service.list_user_sessions.return_value = mock_sessions
        
        # 发送获取列表请求
        response = client.get(
            "/workflows/sessions",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["session_id"] == fixed_session_id
        assert data[0]["status"] == "completed"
        assert data[1]["status"] == "paused" 