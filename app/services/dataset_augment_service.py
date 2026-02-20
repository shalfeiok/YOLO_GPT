"""Создание вариантов датасета: размытие, качество, цвета, разрешение, засветка, затемнение, обесцвечивание."""
import shutil
from pathlib import Path
from typing import Callable
try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None  # type: ignore



def _require_cv2() -> None:
    if cv2 is None:
        raise ImportError("OpenCV (cv2) is required for this feature. Install with: pip install opencv-python")
import numpy as np

# Варианты аугментации (ключ для UI, функция (img_bgr) -> img_bgr)
def _blur(img: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(img, (15, 15), 3)

def _quality_down(img: np.ndarray) -> np.ndarray:
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 55])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)

def _color_shift(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + 25) % 180
    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

def _resolution_down(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    small = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)

def _overexpose(img: np.ndarray) -> np.ndarray:
    return np.clip(img.astype(np.int32) + 60, 0, 255).astype(np.uint8)

def _darken(img: np.ndarray) -> np.ndarray:
    return np.clip(img.astype(np.int32) - 50, 0, 255).astype(np.uint8)

def _desaturate(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


AUGMENT_OPTIONS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "blur": _blur,
    "quality": _quality_down,
    "color_shift": _color_shift,
    "resolution": _resolution_down,
    "overexpose": _overexpose,
    "darken": _darken,
    "desaturate": _desaturate,
}


def _copy_yolo_dataset_structure(source: Path, dest: Path) -> None:
    """Копирует структуру train/images, train/labels, valid/images, valid/labels и data.yaml."""
    for split in ("train", "valid", "val"):
        for sub in ("images", "labels"):
            src_dir = source / split / sub
            if not src_dir.is_dir():
                continue
            dst_dir = dest / split / sub
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in src_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, dst_dir / f.name)
    if (source / "data.yaml").exists():
        shutil.copy2(source / "data.yaml", dest / "data.yaml")


def create_augmented_dataset(
    source_dataset_dir: Path,
    output_dataset_dir: Path,
    options: dict[str, bool],
) -> Path:
    """
    Создаёт новый датасет в output_dataset_dir, применяя выбранные аугментации к каждому изображению
    последовательно. Метки копируются без изменений.
    """
    source_dataset_dir = Path(source_dataset_dir).resolve()
    output_dataset_dir = Path(output_dataset_dir).resolve()
    output_dataset_dir.mkdir(parents=True, exist_ok=True)

    enabled = [k for k, v in options.items() if v and k in AUGMENT_OPTIONS]
    if not enabled:
        _copy_yolo_dataset_structure(source_dataset_dir, output_dataset_dir)
        return output_dataset_dir / "data.yaml"

    for split in ("train", "valid", "val"):
        imgs_dir = source_dataset_dir / split / "images"
        lbls_dir = source_dataset_dir / split / "labels"
        if not imgs_dir.is_dir():
            continue
        out_imgs = output_dataset_dir / split / "images"
        out_lbls = output_dataset_dir / split / "labels"
        out_imgs.mkdir(parents=True, exist_ok=True)
        out_lbls.mkdir(parents=True, exist_ok=True)
        for img_path in imgs_dir.iterdir():
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            for name in enabled:
                img = AUGMENT_OPTIONS[name](img)
            out_img = out_imgs / img_path.name
            cv2.imwrite(str(out_img), img)
            lbl_path = lbls_dir / (img_path.stem + ".txt")
            out_lbl = out_lbls / (img_path.stem + ".txt")
            if lbl_path.exists():
                shutil.copy2(lbl_path, out_lbl)
            else:
                out_lbl.write_text("", encoding="utf-8")

    if (source_dataset_dir / "data.yaml").exists():
        shutil.copy2(source_dataset_dir / "data.yaml", output_dataset_dir / "data.yaml")
    return output_dataset_dir / "data.yaml"
