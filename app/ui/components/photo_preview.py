"""
Окно с вертикальным скроллом и списком изображений (PIL).
Используется для превью датасета с метками и примеров с эффектами аугментации.
"""
from __future__ import annotations

from typing import Sequence

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

PREVIEW_DISPLAY_WIDTH = 900


def _pil_to_qpixmap(pil: Image.Image, max_width: int = PREVIEW_DISPLAY_WIDTH) -> QPixmap:
    img = pil.copy()
    if img.width > max_width:
        ratio = max_width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
    data = img.tobytes("raw", "RGB")
    from PySide6.QtGui import QImage
    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def show_scrollable_photo_dialog(
    parent: QWidget | None,
    title: str,
    images: Sequence[Image.Image] | Sequence[tuple[str, Image.Image]],
    display_width: int = PREVIEW_DISPLAY_WIDTH,
) -> None:
    """
    Открывает диалог с вертикальным скроллом и списком фото.
    images: список PIL.Image или список пар (подпись, PIL.Image).
    """
    if not images:
        return
    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumSize(400, 300)
    d.resize(960, 700)
    layout = QVBoxLayout(d)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: #2b2b2b; border: none; }")
    inner = QWidget()
    inner_layout = QVBoxLayout(inner)
    inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    for item in images:
        if isinstance(item, tuple):
            label_text, pil = item
            lbl_cap = QLabel(label_text)
            lbl_cap.setStyleSheet("background: #2b2b2b; color: #ccc; font-weight: bold; font-size: 11pt; padding: 8px;")
            inner_layout.addWidget(lbl_cap)
            img_to_show = pil
        else:
            img_to_show = item
        pix = _pil_to_qpixmap(img_to_show, display_width)
        lbl_img = QLabel()
        lbl_img.setPixmap(pix)
        lbl_img.setStyleSheet("background: #2b2b2b; padding: 4px;")
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        inner_layout.addWidget(lbl_img)

    scroll.setWidget(inner)
    layout.addWidget(scroll)
    d.exec()
