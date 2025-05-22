"""
模型验证工具

确保模型定义与API使用的一致性
"""
import inspect
import logging
from typing import Dict, List, Type, Any, Optional, get_type_hints

from fastapi import APIRoute, FastAPI, Response
from pydantic import BaseModel

from app.core.config import get_app_settings

logger = logging.getLogger(__name__)


class ValidationError:
    """验证错误信息"""
    def __init__(self, message: str, path: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.path = path
        self.context = context or {}

    def __str__(self):
        return f"{self.path}: {self.message}"


class ModelValidator:
    """模型验证器
    
    用于确保模型定义与API使用的一致性
    """
    
    @classmethod
    def validate_model_consistency(cls, api_route: APIRoute) -> List[ValidationError]:
        """验证API路由的响应模型与模型定义是否一致
        
        Args:
            api_route: API路由
            
        Returns:
            List[ValidationError]: 验证错误列表
        """
        errors = []
        
        if not api_route.response_model:
            return errors
        
        # 获取模型路径
        path = f"{api_route.path}:{api_route.response_model.__name__}"
        
        # 检查响应模型
        model_errors = cls.check_response_model(api_route.response_model, path)
        errors.extend(model_errors)
        
        return errors
    
    @classmethod
    def check_response_model(cls, response_model: Type[BaseModel], endpoint_path: str) -> List[ValidationError]:
        """检查响应模型定义与使用是否一致
        
        Args:
            response_model: 响应模型类
            endpoint_path: 端点路径
            
        Returns:
            List[ValidationError]: 验证错误列表
        """
        errors = []
        
        # 获取模型字段
        try:
            fields = response_model.model_fields
        except AttributeError:
            # Pydantic v1 兼容
            fields = getattr(response_model, "__fields__", {})
        
        if not fields:
            errors.append(ValidationError(
                f"Response model {response_model.__name__} has no fields",
                endpoint_path
            ))
            return errors
        
        # 检查字段类型
        for field_name, field in fields.items():
            field_type = None
            
            # 获取字段类型
            try:
                if hasattr(field, 'type_'):
                    field_type = field.type_
                elif hasattr(field, 'annotation'):
                    field_type = field.annotation
                elif hasattr(field, 'outer_type_'):
                    field_type = field.outer_type_
            except Exception as e:
                errors.append(ValidationError(
                    f"Error getting type for field {field_name}: {str(e)}",
                    f"{endpoint_path}.{field_name}"
                ))
                continue
            
            # 检查嵌套模型
            if field_type and hasattr(field_type, "__origin__") and issubclass(getattr(field_type, "__origin__"), list):
                if hasattr(field_type, "__args__") and len(field_type.__args__) > 0:
                    item_type = field_type.__args__[0]
                    if inspect.isclass(item_type) and issubclass(item_type, BaseModel):
                        nested_errors = cls.check_response_model(
                            item_type, 
                            f"{endpoint_path}.{field_name}[]"
                        )
                        errors.extend(nested_errors)
            
            # 检查嵌套对象类型
            if field_type and inspect.isclass(field_type) and issubclass(field_type, BaseModel):
                nested_errors = cls.check_response_model(
                    field_type, 
                    f"{endpoint_path}.{field_name}"
                )
                errors.extend(nested_errors)
        
        return errors
    
    @classmethod
    def generate_model_documentation(cls, model: Type[BaseModel]) -> str:
        """生成模型文档
        
        Args:
            model: 模型类
            
        Returns:
            str: 模型文档
        """
        doc = [f"# {model.__name__}"]
        
        # 添加模型描述
        if model.__doc__:
            doc.append(inspect.cleandoc(model.__doc__))
        
        # 添加字段信息
        doc.append("\n## Fields\n")
        
        # 获取模型字段
        try:
            fields = model.model_fields
        except AttributeError:
            # Pydantic v1 兼容
            fields = getattr(model, "__fields__", {})
        
        for field_name, field in fields.items():
            field_type = None
            description = None
            required = False
            
            # 获取字段类型和描述
            try:
                if hasattr(field, "annotation"):
                    field_type = field.annotation
                elif hasattr(field, "type_"):
                    field_type = field.type_
                
                if hasattr(field, "description"):
                    description = field.description
                elif hasattr(field, "field_info") and hasattr(field.field_info, "description"):
                    description = field.field_info.description
                
                if hasattr(field, "required"):
                    required = field.required
                elif hasattr(field, "is_required"):
                    required = field.is_required()
            except Exception:
                pass
            
            field_type_str = str(field_type).replace("typing.", "")
            req_str = "required" if required else "optional"
            desc_str = f": {description}" if description else ""
            
            doc.append(f"- **{field_name}** ({field_type_str}, {req_str}){desc_str}")
        
        return "\n\n".join(doc)
    
    @classmethod
    def validate_model_usage_across_layers(cls, model: Type[BaseModel]) -> Dict[str, List[ValidationError]]:
        """验证模型在不同层之间的使用一致性
        
        Args:
            model: 模型类
            
        Returns:
            Dict[str, List[ValidationError]]: 验证错误，按层分组
        """
        errors: Dict[str, List[ValidationError]] = {
            "api_layer": [],
            "service_layer": [],
            "repository_layer": []
        }
        
        # 检查API层使用
        api_usage_errors = cls._check_model_usage_in_api_layer(model)
        errors["api_layer"].extend(api_usage_errors)
        
        # 检查服务层使用
        service_usage_errors = cls._check_model_usage_in_service_layer(model)
        errors["service_layer"].extend(service_usage_errors)
        
        # 检查仓库层使用
        repository_usage_errors = cls._check_model_usage_in_repository_layer(model)
        errors["repository_layer"].extend(repository_usage_errors)
        
        return {k: v for k, v in errors.items() if v}
    
    @classmethod
    def _check_model_usage_in_api_layer(cls, model: Type[BaseModel]) -> List[ValidationError]:
        """检查模型在API层的使用
        
        Args:
            model: 模型类
            
        Returns:
            List[ValidationError]: 验证错误列表
        """
        # 具体实现可能需要根据项目结构调整
        return []
    
    @classmethod
    def _check_model_usage_in_service_layer(cls, model: Type[BaseModel]) -> List[ValidationError]:
        """检查模型在服务层的使用
        
        Args:
            model: 模型类
            
        Returns:
            List[ValidationError]: 验证错误列表
        """
        # 具体实现可能需要根据项目结构调整
        return []
    
    @classmethod
    def _check_model_usage_in_repository_layer(cls, model: Type[BaseModel]) -> List[ValidationError]:
        """检查模型在仓库层的使用
        
        Args:
            model: 模型类
            
        Returns:
            List[ValidationError]: 验证错误列表
        """
        # 具体实现可能需要根据项目结构调整
        return []


class ModelConsistencyTestCase:
    """模型一致性测试用例基类
    
    提供测试API模型与实现一致性的方法
    """
    
    def test_model_endpoints_consistency(self) -> None:
        """测试所有API端点响应模型与模型定义的一致性"""
        app = self._get_test_app()
        errors = []
        
        for route in app.routes:
            if isinstance(route, APIRoute) and route.response_model:
                route_errors = ModelValidator.validate_model_consistency(route)
                errors.extend(route_errors)
        
        assert not errors, f"Found {len(errors)} model consistency issues:\n" + "\n".join(str(e) for e in errors)
    
    def test_service_model_alignment(self) -> None:
        """测试服务层与API层模型使用的一致性"""
        # 实现依赖于具体的测试框架和项目结构
        pass
    
    def _get_test_app(self) -> FastAPI:
        """获取测试应用实例
        
        Returns:
            FastAPI: 测试应用实例
        """
        # 实现依赖于具体的测试框架和项目结构
        from app.main import app
        return app


def validate_models_on_startup(app: FastAPI) -> None:
    """在应用启动时验证所有模型定义与API使用的一致性
    
    Args:
        app: FastAPI应用实例
    """
    settings = get_app_settings()
    
    # 在开发环境中启用，在生产环境中禁用
    if settings.debug:
        errors = []
        for route in app.routes:
            if isinstance(route, APIRoute) and route.response_model:
                route_errors = ModelValidator.validate_model_consistency(route)
                errors.extend(route_errors)
        
        if errors:
            # 仅在开发环境中，打印出所有模型一致性错误
            for error in errors:
                logger.warning(f"Model consistency error: {error}") 