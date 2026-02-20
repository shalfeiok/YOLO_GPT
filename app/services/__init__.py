"""Сервисы приложения: датасеты, обучение, детекция, захват кадров, аугментация, визуализация."""

from .dataset_service import DatasetConfigBuilder
from .training_service import TrainingService
from .detection_service import DetectionService
from .capture_service import WindowCaptureService, OpenCVFrameSource
from .yolo_prep_service import (
    convert_voc_to_yolo,
    is_voc_dataset,
    prepare_for_yolo,
    export_dataset_filter_classes,
    merge_classes_in_dataset,
    rename_class_in_dataset,
)
from .dataset_augment_service import create_augmented_dataset, AUGMENT_OPTIONS
from .dataset_visualize import (
    load_classes_from_dataset,
    draw_boxes,
    get_sample_image_path,
    get_sample_image_paths,
    get_labels_path_for_image,
)

__all__ = [
    "DatasetConfigBuilder",
    "TrainingService",
    "DetectionService",
    "WindowCaptureService",
    "OpenCVFrameSource",
    "convert_voc_to_yolo",
    "is_voc_dataset",
    "prepare_for_yolo",
    "export_dataset_filter_classes",
    "merge_classes_in_dataset",
    "rename_class_in_dataset",
    "create_augmented_dataset",
    "AUGMENT_OPTIONS",
    "load_classes_from_dataset",
    "draw_boxes",
    "get_sample_image_path",
    "get_sample_image_paths",
    "get_labels_path_for_image",
]
