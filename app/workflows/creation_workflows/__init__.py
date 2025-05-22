"""
创作工作流包，实现各种类型的创作模式和流程控制
"""

from .base_workflow import CreationWorkflow, CreationState
from .free_workflow import FreeCreationWorkflow
from .guided_workflow import GuidedCreationWorkflow
from .structured_workflow import StructuredCreationWorkflow
from .workflow_factory import WorkflowFactory, WorkflowRegistry
from .workflow_manager import WorkflowManager

__all__ = [
    'CreationWorkflow',
    'CreationState',
    'FreeCreationWorkflow',
    'GuidedCreationWorkflow',
    'StructuredCreationWorkflow',
    'WorkflowFactory',
    'WorkflowRegistry',
    'WorkflowManager',
]
