"""
素材处理器同步实现暴露（异步实现已移除）
"""

from .sync_material_analyzer import SyncMaterialAnalyzer
from .sync_material_processor import SyncMaterialProcessor

__all__ = ["SyncMaterialProcessor", "SyncMaterialAnalyzer"]
