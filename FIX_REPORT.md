# FIX_REPORT

## Summary
Исправлены две проблемы детекции: (1) при включённых live-фичах вывод шел только в stdout (PyCharm), но не попадал в логи Jobs; (2) окно превью при каждом старте могло иметь разный размер из‑за нестабильного имени окна и непоследовательного применения resize. Теперь вывод из детекционного потока прокидывается в `JobLogLine`, а окно визуализации использует стабильное имя и принудительное применение размеров из настроек.

## Issues Found

### Logs / Observability
- Сообщения из live-фич (Ultralytics solutions) печатались в stdout/stderr внутри потока детекции, поэтому в Jobs лог был пустой.

### Visualization settings
- Бэкенды визуализации формировали отдельное имя окна на каждый run (`YOLO_<run_id>`), из-за чего поведение размера окна было непредсказуемым.
- Размер окна применялся не всегда стабильно на старте/рендере.

## Fixes Applied
- `app/ui/views/detection/view.py`
  - добавлен захват stdout/stderr в inference-loop через `contextlib.redirect_stdout/redirect_stderr`;
  - строки из вывода публикуются в `JobLogLine` текущей detection-задачи;
  - имя окна превью сделано стабильным (`CV2_WIN_NAME`) для единообразного поведения между запусками.
- `app/features/detection_visualization/backends/opencv_backend.py`
  - окно теперь создается по переданному `window_name` (sanitized), а не по `run_id`;
  - при активных `preview_max_w/h` выполняется `resizeWindow` и после `imshow` для стабилизации размера.
- `app/features/detection_visualization/backends/d3dshot_pytorch_backend.py`
  - аналогично: переход на стабильное имя окна + повторное применение `resizeWindow` при рендере.

## Verification Checklist
- `python -m compileall .`
- `pytest -q`
- `ruff check .`
- `ruff format app/ui/views/detection/view.py app/features/detection_visualization/backends/opencv_backend.py app/features/detection_visualization/backends/d3dshot_pytorch_backend.py`

## Manual QA
1. Включить live-фичи в Detection и нажать «Старт».
2. Проверить вкладку Jobs: в логе должны появляться строки, которые ранее были только в консоли IDE.
3. Задать `preview_max_w/h` в настройках визуализации и несколько раз перезапустить детекцию без изменения конфига.
4. Убедиться, что размер окна стабилен между запусками.
