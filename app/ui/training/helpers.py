"""Вспомогательные функции вкладки «Обучение» (SOLID: чистые функции, тестируемы)."""
from pathlib import Path
from time import monotonic

# Кэш результатов scan_trained_weights на 3 с, чтобы не сканировать диск при каждом открытии меню
_CACHE_SCAN: tuple[float, Path, list[tuple[str, Path]]] | None = None
_CACHE_TTL_S = 3.0


def scan_trained_weights(project_root: Path) -> list[tuple[str, Path]]:
    """Находит runs/train/*/weights/best.pt и возвращает [(подпись_для_UI, путь)].

    Результат кэшируется на несколько секунд, чтобы снизить число обращений к ФС
    при частом открытии выпадающего списка моделей.

    Args:
        project_root: Корень проекта (каталог с runs/).

    Returns:
        Список пар (отображаемая подпись, абсолютный путь к best.pt).
    """
    global _CACHE_SCAN
    now = monotonic()
    if _CACHE_SCAN is not None:
        cached_at, cached_root, result = _CACHE_SCAN
        if cached_root == project_root and (now - cached_at) < _CACHE_TTL_S:
            return result
    out: list[tuple[str, Path]] = []
    train_dir = project_root / "runs" / "train"
    if train_dir.is_dir():
        for run_dir in train_dir.iterdir():
            if not run_dir.is_dir():
                continue
            best = run_dir / "weights" / "best.pt"
            if best.exists():
                try:
                    rel = best.relative_to(project_root)
                except ValueError:
                    rel = best
                out.append((f"Наша: {rel}", best.resolve()))
    _CACHE_SCAN = (now, project_root, out)
    return out
