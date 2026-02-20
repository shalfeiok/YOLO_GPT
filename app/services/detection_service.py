"""Реэкспорт DetectionService из yolo_inference.

Логика детекции и загрузки модели находится в app.yolo_inference (по правилу проекта не изменять).
"""

from app.yolo_inference import DetectionService

__all__ = ["DetectionService"]
