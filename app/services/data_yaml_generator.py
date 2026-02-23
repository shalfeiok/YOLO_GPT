from __future__ import annotations

import csv
import logging
import shutil
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VISDRONE_DEFAULT_NAMES = {
    0: "pedestrian",
    1: "people",
    2: "bicycle",
    3: "car",
    4: "van",
    5: "truck",
    6: "tricycle",
    7: "awning-tricycle",
    8: "bus",
    9: "motor",
}

DatasetType = Literal["YOLO_READY", "DET", "VID", "SOT", "CC", "UNKNOWN"]
Confidence = Literal["low", "medium", "high"]


@dataclass(slots=True)
class DatasetTypeDetectionResult:
    dataset_type: DatasetType
    confidence: Confidence
    evidence: list[str]


@dataclass(slots=True)
class LayoutResolveResult:
    train: str | None
    val: str | None
    test: str | list[str] | None
    warnings: list[str]


@dataclass(slots=True)
class NamesResolveResult:
    names: dict[int, str]
    nc: int
    source: str
    warnings: list[str]


@dataclass(slots=True)
class DataYamlBuildResult:
    data_yaml_path: Path
    detected_type: DatasetType
    confidence: Confidence
    evidence: list[str]
    train: str | None
    val: str | None
    test: str | list[str] | None
    names: dict[int, str]
    names_source: str
    warnings: list[str]


class DatasetTypeDetector:
    """Detect dataset family with lightweight heuristics and explainable evidence."""

    def detect(self, dataset_root: Path) -> DatasetTypeDetectionResult:
        root = Path(dataset_root)
        evidence: list[str] = []

        if self._is_yolo_ready(root, evidence):
            return DatasetTypeDetectionResult("YOLO_READY", "high", evidence)

        vid_score, vid_evidence = self._score_vid(root)
        sot_score, sot_evidence = self._score_sot(root)
        det_score, det_evidence = self._score_det(root)
        cc_score, cc_evidence = self._score_cc(root)
        evidence.extend(vid_evidence + sot_evidence + det_evidence + cc_evidence)

        scored = [("VID", vid_score), ("SOT", sot_score), ("DET", det_score), ("CC", cc_score)]
        best_type, best_score = max(scored, key=lambda item: item[1])
        if best_score >= 3:
            confidence: Confidence = "high" if best_score >= 5 else "medium"
            return DatasetTypeDetectionResult(best_type, confidence, evidence)

        evidence.append("No stable signature matched; falling back to UNKNOWN")
        return DatasetTypeDetectionResult("UNKNOWN", "low", evidence)

    def _is_yolo_ready(self, root: Path, evidence: list[str]) -> bool:
        for split in ["train", "val", "valid", "test"]:
            images_dir = root / split / "images"
            labels_dir = root / split / "labels"
            if images_dir.is_dir() and labels_dir.is_dir() and _has_images(images_dir):
                if self._has_yolo_5col_rows(labels_dir):
                    evidence.append(f"YOLO pattern found in {split}/images + {split}/labels")
                    return True

        for images_dir in [p for p in root.rglob("images") if p.is_dir()]:
            sibling_labels = images_dir.parent / "labels"
            if sibling_labels.is_dir() and self._has_yolo_5col_rows(sibling_labels):
                evidence.append(f"YOLO sibling layout found: {images_dir.relative_to(root).as_posix()}")
                return True
        return False

    def _has_yolo_5col_rows(self, labels_dir: Path) -> bool:
        sample_files = list(labels_dir.rglob("*.txt"))[:20]
        for txt in sample_files:
            for line in txt.read_text(encoding="utf-8", errors="ignore").splitlines()[:30]:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    cls_id = int(parts[0])
                    nums = [float(v) for v in parts[1:5]]
                except ValueError:
                    continue
                if cls_id >= 0 and all(0.0 <= n <= 1.0 for n in nums):
                    return True
        return False

    def _score_vid(self, root: Path) -> tuple[int, list[str]]:
        score = 0
        evidence: list[str] = []
        for split in [p for p in root.iterdir() if p.is_dir()]:
            seq = split / "sequences"
            ann = split / "annotations"
            if not (seq.is_dir() and ann.is_dir()):
                continue
            score += 2
            evidence.append(f"VID candidate split: {split.name} has sequences+annotations")
            rows10 = 0
            for txt in list(ann.glob("*.txt"))[:5]:
                rows10 += _count_matching_rows(txt, _is_vid_row, max_rows=120)
            if rows10 >= 20:
                score += 4
                evidence.append(f"VID annotation signature found in {split.name} (>=20 rows with 10 columns)")
        return score, evidence

    def _score_sot(self, root: Path) -> tuple[int, list[str]]:
        score = 0
        evidence: list[str] = []
        has_sequences = any((p / "sequences").is_dir() for p in root.iterdir() if p.is_dir())
        if has_sequences:
            score += 1
            evidence.append("SOT candidate: sequences directories exist")
        bbox_like_rows = 0
        for ann_dir in [p for p in root.rglob("annotations") if p.is_dir()]:
            for txt in list(ann_dir.glob("*.txt"))[:8]:
                bbox_like_rows += _count_matching_rows(txt, _is_sot_row, max_rows=120)
        if bbox_like_rows >= 20:
            score += 3
            evidence.append("SOT signature found (bbox-only 4/5 column rows)")
        return score, evidence

    def _score_det(self, root: Path) -> tuple[int, list[str]]:
        score = 0
        evidence: list[str] = []
        for split in [p for p in root.iterdir() if p.is_dir()]:
            images = split / "images"
            ann = split / "annotations"
            if not (images.is_dir() and ann.is_dir() and _has_images(images)):
                continue
            score += 2
            evidence.append(f"DET candidate split: {split.name} has images+annotations")
            det_rows = 0
            for txt in list(ann.glob("*.txt"))[:10]:
                det_rows += _count_matching_rows(txt, _is_det_row, max_rows=60)
            if det_rows >= 10:
                score += 3
                evidence.append(f"DET annotation signature found in {split.name}")
        return score, evidence

    def _score_cc(self, root: Path) -> tuple[int, list[str]]:
        score = 0
        evidence: list[str] = []
        cc_rows = 0
        for ann_dir in [p for p in root.rglob("annotations") if p.is_dir()]:
            for txt in list(ann_dir.glob("*.txt"))[:10]:
                cc_rows += _count_matching_rows(txt, _is_cc_row, max_rows=80)
        if cc_rows >= 20:
            score += 4
            evidence.append("CC signature found (frame,count style rows)")
        return score, evidence


class DatasetLayoutResolver:
    def resolve(self, dataset_root: Path, _dataset_type: DatasetType) -> LayoutResolveResult:
        root = Path(dataset_root)
        warnings: list[str] = []

        list_result = self._resolve_list_files(root)
        if list_result is not None:
            train, val, test = list_result
            if val is None:
                warnings.append("split 'val' not found")
            return LayoutResolveResult(train=train, val=val, test=test, warnings=warnings)

        train: str | None = None
        val: str | None = None
        tests: list[str] = []

        for split_dir in sorted([d for d in root.iterdir() if d.is_dir()], key=lambda p: p.name.lower()):
            split_name = split_dir.name.lower()
            images_root = self._detect_images_root(split_dir)
            if images_root is None:
                if split_name.startswith("test"):
                    if "initialization" in split_name:
                        warnings.append(f"initialization-only split skipped: {split_dir.name}")
                    else:
                        warnings.append(f"split contains no images, skipped: {split_dir.name}")
                continue

            rel_path = _rel(images_root, root)
            if split_name.startswith("train") and train is None:
                train = rel_path
            elif split_name.startswith(("val", "valid", "validation")) and val is None:
                val = rel_path
            elif split_name.startswith("test"):
                tests.append(rel_path)

        if val is None:
            warnings.append("split 'val' not found")

        test: str | list[str] | None = None
        if tests:
            test = tests[0] if len(tests) == 1 else tests

        return LayoutResolveResult(train=train, val=val, test=test, warnings=warnings)

    def _resolve_list_files(self, root: Path) -> tuple[str | None, str | None, str | list[str] | None] | None:
        list_files = sorted([p for p in root.glob("*list.txt") if p.is_file()])
        if not list_files:
            return None

        train = _first_rel_by_stem(root, list_files, ("trainlist",))
        val = _first_rel_by_stem(root, list_files, ("vallist", "validlist", "validationlist"))

        test_lists = [
            _rel(p, root)
            for p in list_files
            if p.stem.lower().startswith("test") and p.stem.lower().endswith("list")
        ]
        test: str | list[str] | None = None
        if test_lists:
            test = test_lists[0] if len(test_lists) == 1 else test_lists
        return train, val, test

    def _detect_images_root(self, split_dir: Path) -> Path | None:
        for preferred in ("images", "sequences"):
            candidate = split_dir / preferred
            if candidate.is_dir() and _has_images(candidate):
                return candidate

        best: Path | None = None
        best_count = 0
        for child in [p for p in split_dir.iterdir() if p.is_dir()]:
            count = _count_images(child)
            if count > best_count:
                best = child
                best_count = count
        return best


class NamesResolver:
    YAML_CANDIDATES = ("data.yaml", "dataset.yaml", "yolo.yaml", "yolov8.yaml")
    TXT_CANDIDATES = ("classes.txt", "names.txt", "obj.names")

    def resolve(self, dataset_root: Path, detected_type: DatasetType) -> NamesResolveResult:
        root = Path(dataset_root)
        warnings: list[str] = []

        from_yaml = self._resolve_from_yaml(root)
        if from_yaml is not None:
            names, source = from_yaml
            return NamesResolveResult(names=names, nc=len(names), source=source, warnings=warnings)

        from_txt = self._resolve_from_classes_files(root)
        if from_txt is not None:
            names, source = from_txt
            return NamesResolveResult(names=names, nc=len(names), source=source, warnings=warnings)

        if detected_type in {"DET", "VID"}:
            return NamesResolveResult(
                names=dict(VISDRONE_DEFAULT_NAMES),
                nc=10,
                source="visdrone_defaults",
                warnings=warnings,
            )

        if detected_type == "SOT":
            warnings.append("SOT is not detection dataset; generated nc=1 default")
            return NamesResolveResult(names={0: "object"}, nc=1, source="sot_default", warnings=warnings)

        if detected_type == "CC":
            warnings.append("CC is crowd counting; data.yaml is for detection; generated placeholder")
            return NamesResolveResult(names={0: "person"}, nc=1, source="cc_placeholder", warnings=warnings)

        inferred_max = _infer_max_class_from_yolo_labels(root)
        if inferred_max is not None:
            warnings.append("No class names sources found; placeholder names were generated")
            names = {idx: f"class{idx}" for idx in range(inferred_max + 1)}
            return NamesResolveResult(names=names, nc=len(names), source="labels_inference", warnings=warnings)

        warnings.append("No class names sources found; placeholder names were generated")
        return NamesResolveResult(names={0: "class0"}, nc=1, source="fallback_default", warnings=warnings)

    def _resolve_from_yaml(self, root: Path) -> tuple[dict[int, str], str] | None:
        for yaml_name in self.YAML_CANDIDATES:
            yaml_path = root / yaml_name
            if not yaml_path.exists():
                continue
            data = _load_yaml_dict(yaml_path)
            names = _extract_names(data)
            if names:
                return names, f"{yaml_name}:names"
        return None

    def _resolve_from_classes_files(self, root: Path) -> tuple[dict[int, str], str] | None:
        for txt_name in self.TXT_CANDIDATES:
            txt_path = root / txt_name
            if not txt_path.exists():
                continue
            lines = []
            for line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                clean = line.strip()
                if not clean or clean.startswith("#"):
                    continue
                lines.append(clean)
            if lines:
                return {idx: name for idx, name in enumerate(lines)}, txt_name
        return None


class DataYamlWriter:
    def write(
        self,
        *,
        dataset_root: Path,
        layout: LayoutResolveResult,
        names: NamesResolveResult,
        detection: DatasetTypeDetectionResult,
        warnings: list[str],
    ) -> DataYamlBuildResult:
        root = Path(dataset_root)
        output_path = root / "data.yaml"
        if output_path.exists():
            shutil.copy2(output_path, output_path.with_suffix(".yaml.bak"))

        payload: OrderedDict[str, Any] = OrderedDict()
        payload["path"] = "."
        if layout.train is not None:
            payload["train"] = layout.train
        if layout.val is not None:
            payload["val"] = layout.val
        if layout.test is not None:
            payload["test"] = layout.test
        payload["nc"] = names.nc
        payload["names"] = {idx: names.names[idx] for idx in sorted(names.names)}

        with output_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                dict(payload),
                fh,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )

        return DataYamlBuildResult(
            data_yaml_path=output_path,
            detected_type=detection.dataset_type,
            confidence=detection.confidence,
            evidence=detection.evidence,
            train=layout.train,
            val=layout.val,
            test=layout.test,
            names=names.names,
            names_source=names.source,
            warnings=warnings,
        )


class CreateDataYamlUseCase:
    def __init__(
        self,
        detector: DatasetTypeDetector | None = None,
        layout_resolver: DatasetLayoutResolver | None = None,
        names_resolver: NamesResolver | None = None,
        writer: DataYamlWriter | None = None,
    ) -> None:
        self._detector = detector or DatasetTypeDetector()
        self._layout_resolver = layout_resolver or DatasetLayoutResolver()
        self._names_resolver = names_resolver or NamesResolver()
        self._writer = writer or DataYamlWriter()

    def run(self, dataset_root: Path) -> DataYamlBuildResult:
        root = self._normalize_dataset_root(Path(dataset_root).resolve())
        detection = self._detector.detect(root)
        layout = self._layout_resolver.resolve(root, detection.dataset_type)
        names = self._names_resolver.resolve(root, detection.dataset_type)
        warnings = [*layout.warnings, *names.warnings]
        result = self._writer.write(
            dataset_root=root,
            layout=layout,
            names=names,
            detection=detection,
            warnings=warnings,
        )
        logger.info(
            "data.yaml created: path=%s type=%s train=%s val=%s test=%s names_source=%s warnings=%s",
            result.data_yaml_path,
            result.detected_type,
            result.train,
            result.val,
            result.test,
            result.names_source,
            result.warnings,
        )
        return result

    def _normalize_dataset_root(self, root: Path) -> Path:
        if root.name.lower().startswith(("train", "val", "valid", "test")):
            parent = root.parent
            sibling_dirs = [p.name.lower() for p in parent.iterdir() if p.is_dir()]
            has_pair = any(name.startswith("train") for name in sibling_dirs) and any(
                name.startswith(("val", "valid", "test")) for name in sibling_dirs
            )
            if has_pair:
                return parent
        return root


def generate_data_yaml(dataset_root: Path) -> DataYamlBuildResult:
    return CreateDataYamlUseCase().run(dataset_root)


def _first_rel_by_stem(root: Path, files: list[Path], stems: tuple[str, ...]) -> str | None:
    for stem in stems:
        for file_path in files:
            if file_path.stem.lower() == stem:
                return _rel(file_path, root)
    return None


def _has_images(path: Path) -> bool:
    return any(p.is_file() and p.suffix.lower() in _IMAGE_EXTS for p in path.rglob("*"))


def _count_images(path: Path) -> int:
    return sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTS)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _count_matching_rows(path: Path, predicate: Any, *, max_rows: int) -> int:
    count = 0
    rows = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        rows += 1
        if predicate(line):
            count += 1
        if rows >= max_rows:
            break
    return count


def _split_csv_or_space(line: str) -> list[str]:
    if "," in line:
        reader = csv.reader([line])
        return [part.strip() for part in next(reader)]
    return [part.strip() for part in line.split() if part.strip()]


def _is_vid_row(line: str) -> bool:
    parts = _split_csv_or_space(line)
    if len(parts) != 10:
        return False
    try:
        frame_id = int(float(parts[0]))
        _ = [float(v) for v in parts[1:]]
    except ValueError:
        return False
    return frame_id > 0


def _is_sot_row(line: str) -> bool:
    parts = _split_csv_or_space(line)
    if len(parts) not in {4, 5}:
        return False
    try:
        _ = [float(v) for v in parts]
    except ValueError:
        return False
    return True


def _is_det_row(line: str) -> bool:
    parts = _split_csv_or_space(line)
    if len(parts) < 8:
        return False
    try:
        category = int(float(parts[5]))
        _ = [float(v) for v in parts[:8]]
    except ValueError:
        return False
    return 0 <= category <= 10


def _is_cc_row(line: str) -> bool:
    parts = _split_csv_or_space(line)
    if len(parts) != 2:
        return False
    left, right = parts
    if not left:
        return False
    if not left.replace(".", "", 1).isdigit() and not left.endswith(('.jpg', '.png', '.jpeg')):
        return False
    try:
        float(right)
    except ValueError:
        return False
    return True


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return raw if isinstance(raw, dict) else {}


def _extract_names(data: dict[str, Any]) -> dict[int, str]:
    names = data.get("names")
    if isinstance(names, list):
        return {idx: str(name) for idx, name in enumerate(names)}
    if isinstance(names, dict):
        out: dict[int, str] = {}
        for key, value in names.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            out[idx] = str(value)
        if out:
            return {idx: out[idx] for idx in sorted(out)}
    return {}


def _infer_max_class_from_yolo_labels(root: Path) -> int | None:
    label_dirs = [p for p in root.rglob("labels") if p.is_dir()]
    max_id: int | None = None
    for labels_dir in label_dirs:
        for txt in labels_dir.rglob("*.txt"):
            for line in txt.read_text(encoding="utf-8", errors="ignore").splitlines()[:200]:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    cls_id = int(parts[0])
                    values = [float(v) for v in parts[1:5]]
                except ValueError:
                    continue
                if cls_id >= 0 and all(0.0 <= n <= 1.0 for n in values):
                    max_id = cls_id if max_id is None else max(max_id, cls_id)
    return max_id
