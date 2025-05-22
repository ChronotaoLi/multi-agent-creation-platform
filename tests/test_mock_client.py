"""
测试模拟客户端响应的测试模块
"""
import pytest
from unittest.mock import MagicMock

def test_mock_client_complete_workflow(client):
    """测试模拟客户端处理工作流完成请求"""
    session_id = "954f8b0d-f98e-4830-b252-7dd936b2bc2f"
    
    # 发送完成请求
    response = client.post(
        f"/workflows/sessions/{session_id}/complete",
        headers={"Authorization": "Bearer test_token"}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    assert "content" in data
    assert "title" in data["content"]
    assert "characters" in data["content"]
    assert "plot_points" in data["content"] 