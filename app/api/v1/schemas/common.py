"""
通用的请求/响应Pydantic模型

定义API通用的请求和响应数据结构
"""
from enum import Enum
from typing import Generic, TypeVar, List, Optional, Any, Dict, Union
from typing_extensions import Annotated

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic.generics import GenericModel


# 定义用于泛型模型的类型变量
T = TypeVar('T')


class SortOrder(str, Enum):
    """排序顺序枚举"""
    asc = "asc"
    desc = "desc"


class PaginationParams(BaseModel):
    """分页参数模型
    
    用于处理分页请求
    """
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页项目数")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: SortOrder = Field(SortOrder.desc, description="排序顺序")


class Page(GenericModel, Generic[T]):
    """分页结果响应模型
    
    包含分页信息和结果项目列表
    """
    items: List[T] = Field(..., description="结果项目列表")
    total: int = Field(..., description="总项目数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页项目数")
    pages: int = Field(..., description="总页数")
    
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel):
    """API响应基类
    
    基本的API响应结构
    """
    status: str = Field(..., description="响应状态（success/error）")
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")


class ErrorResponse(BaseModel):
    """错误响应模型
    
    用于返回错误信息
    """
    status: str = Field("error", description="响应状态")
    message: str = Field(..., description="错误消息")
    detail: Optional[Any] = Field(None, description="错误详情")
    code: Optional[str] = Field(None, description="错误代码")


class ValidationErrorItem(BaseModel):
    """验证错误项目
    
    单个字段的验证错误信息
    """
    loc: List[Union[str, int]] = Field(..., description="错误位置")
    msg: str = Field(..., description="错误消息")
    type: str = Field(..., description="错误类型")


class ValidationErrorResponse(ErrorResponse):
    """验证错误响应
    
    用于返回请求参数验证错误
    """
    status: str = Field("error", description="响应状态")
    message: str = Field("验证错误", description="错误消息")
    detail: List[ValidationErrorItem] = Field(..., description="验证错误详情")
    code: str = Field("validation_error", description="错误代码")


class SuccessResponse(ApiResponse):
    """成功响应模型
    
    用于返回操作成功信息
    """
    status: str = Field("success", description="响应状态")
    message: str = Field(..., description="成功消息")


class EmptyResponse(BaseModel):
    """空响应模型
    
    用于没有返回内容的请求
    """
    pass


class DeleteResponse(SuccessResponse):
    """删除操作响应
    
    用于删除操作的响应
    """
    message: str = Field("删除成功", description="成功消息")


class FilterParams(BaseModel):
    """过滤参数基础模型
    
    用于构建查询过滤条件
    """
    search: Optional[str] = Field(None, description="搜索关键词")
    order_by: Optional[str] = Field(None, description="排序字段")
    order_direction: SortOrder = Field(SortOrder.desc, description="排序方向")
    
    model_config = ConfigDict(extra='allow')
