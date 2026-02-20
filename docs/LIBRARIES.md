# Библиотеки проекта YOLO_3 и где они используются

## Окна приложения (главное окно — PySide6)

| Окно/вкладка | ID вкладки | Описание |
|--------------|------------|----------|
| **Главное окно** | — | PySide6 (Qt): сайдбар, стек контента, палитра команд (Ctrl+K), статус-бар |
| **Датасеты** | `datasets` | Управление датасетами, конвертация в YOLO, превью фото, аугментация |
| **Обучение** | `training` | Обучение YOLO: модель, датасеты, эпохи, метрики в реальном времени, дашборд |
| **Детекция** | `detection` | Модель, источник (экран/окно/камера/видео), conf/IOU, отрисовка (OpenCV/D3DShot/ONNX), Старт/Стоп, FPS, превью в отдельном окне OpenCV |
| **Интеграции** | `integrations` | Comet, DVC, SageMaker, K-Fold, Tuning, Export, SAHI, Seg Isolation, Validation и др. |

---

## Библиотеки: за что отвечают и в каком окне

| Библиотека | Назначение | Где используется (окно/модуль) |
|------------|------------|----------------------------------|
| **PySide6** | Основной GUI: окна, виджеты, темы, навигация | Главное окно, сайдбар, все вкладки (Датасеты, Обучение, Детекция, Интеграции), диалоги, кнопки, карточки, тосты, палитра команд |
| **customtkinter** | Legacy GUI (архив примеров) | В production-коде не используется; legacy-реализации вынесены в `examples/tk_ui/*`, а `app/features/*/ui.py` содержат безопасные stubs |
| **opencv-python (cv2)** | Захват/видео, ресайз, отрисовка, превью детекции | **Детекция**: превью (imshow), ресайз; бэкенды отрисовки (opencv_backend, d3dshot_pytorch_backend); **Датасеты**: чтение/превью изображений; **ONNX-детектор**: препроцессинг, NMS, рисование боксов; **Capture**: камера/видео (OpenCVFrameSource) |
| **numpy** | Массивы, тензоры, обмен с OpenCV/PyTorch/ONNX | Детекция (кадры, аннотации), бэкенды визуализации, ONNX-детектор, датасеты (изображения), сервисы датасетов |
| **Pillow (PIL)** | Работа с изображениями (открытие, конвертация) | **Датасеты**: превью и галерея фото (Image.fromarray, BGR→RGB) |
| **ultralytics** | Обучение и инференс YOLO, Solutions (Heatmap, Counter и т.д.) | **Обучение**: `TrainingService` (YOLO train); **Детекция**: `DetectionService` (YOLO predict), Ultralytics Solutions в превью; **Интеграции**: K-Fold, Tuning, Export, Validation — везде через `YOLO()`; **model_export**: экспорт в ONNX/OpenVINO/TF и др. |
| **onnxruntime** | Инференс YOLO в формате ONNX (CPU/GPU) | **Детекция**: вариант отрисовки «ONNX» — `OnnxDetectionService` в `yolo_inference/onnx_detector.py` |
| **pywin32** (win32gui, win32ui, win32con, win32api) | Захват окон и экрана на Windows (GDI, PrintWindow, BitBlt) | **Детекция**: `WindowCaptureService` в `capture_service.py` — список окон, захват окна/экрана |
| **mss** | Кроссплатформенный захват экрана (fallback/основной для «Весь экран») | **Детекция**: `WindowCaptureService` — захват региона/монитора когда нет D3DShot |
| **d3dshot** (опционально) | Захват экрана через Direct3D (Windows) | **Детекция**: бэкенд «D3DShot + PyTorch» — захват «Весь экран», быстрый путь с GPU-тензорами |
| **psutil** | CPU и RAM | **Обучение**: вкладка «Обучение» — отображение загрузки CPU и памяти в UI |
| **nvidia-ml-py (pynvml)** | Метрики GPU NVIDIA | **Обучение**: вкладка «Обучение» — загрузка GPU, память, температура (fallback: nvidia-smi) |
| **pyqtgraph** | Графики метрик обучения в реальном времени | **Обучение**: виджет дашборда метрик (loss: box_loss, cls_loss, dfl_loss), зум, панорама, курсор |
| **PyYAML** | Чтение/запись data.yaml и конфигов | **Обучение**: data.yaml для обучения; **Интеграции**: K-Fold, Tuning, Validation — пути к data.yaml; **Сервисы**: `yolo_prep_service` — создание/обновление data.yaml при подготовке датасетов |
| **albumentations** | Аугментации при обучении YOLO | **Обучение**: диалог «Доп. настройки» — интеграция Albumentations; **TrainingService**: применение трансформов из конфига при train |

---

## Дополнительно

| Библиотека | Назначение | Где |
|------------|------------|-----|
| **json** (stdlib) | Конфиги (например, detection_visualization, integrations) | Загрузка/сохранение JSON-настроек по всему приложению |
| **pytest** | Тесты | Запуск тестов проекта |

---

## Сводка: окно → ключевые библиотеки

| Окно | Ключевые библиотеки |
|------|----------------------|
| **Главное окно** | PySide6 |
| **Датасеты** | PySide6, OpenCV, numpy, Pillow, PyYAML (через сервисы подготовки) |
| **Обучение** | PySide6, ultralytics, pyqtgraph, psutil, nvidia-ml-py, PyYAML, albumentations |
| **Детекция** | PySide6, OpenCV, numpy, ultralytics, onnxruntime, pywin32, mss, d3dshot (опционально) |
| **Интеграции** | PySide6, ultralytics, PyYAML (и зависимости конкретных интеграций) |

Точка входа: `main.py` — создаётся Qt-приложение (PySide6), главное окно с вкладками `datasets`, `training`, `detection`, `integrations`. `customtkinter` не участвует в production runtime: legacy Tk UI вынесен в `examples/tk_ui`, а модули `app/features/*/ui.py` оставлены как stubs с явным сообщением о переносе.
