# Логика приложения YOLO Desktop Studio

## 1. Точка входа и запуск

**Файл:** `main.py`

- Подавляется предупреждение PyTorch/CUDA по pynvml.
- Создаётся Qt-приложение: `create_application()` (High DPI, имя/организация для QSettings).
- Создаётся `AppSettings` (QSettings: геометрия, тема, сайдбар).
- Создаётся глобальный `ThemeManager(settings)`, восстанавливается тема из настроек (`set_theme(settings.get_theme())`).
- Создаётся **Container** (DI) и **TrainingSignals** (сигналы обучения).
- Создаётся **MainWindow(settings, container, signals)** и показывается.
- Запускается цикл событий: `run_application(app)` → `app.exec()`.

Приложение живёт до закрытия главного окна; при закрытии сохраняется геометрия и состояние.

---

## 2. DI-контейнер (Container)

**Файл:** `app/ui/infrastructure/di.py`

Единственное место, где создаются сервисы. Ленивая инициализация: экземпляр создаётся при первом обращении к свойству.

- **trainer** → `TrainingService()` — обучение YOLO в фоне.
- **detector** → `DetectionService()` — инференс Ultralytics (PyTorch) по кадру.
- **detector_onnx** → `OnnxDetectionService()` — инференс через ONNX Runtime (.pt при необходимости экспортируется в .onnx).
- **window_capture** → `WindowCaptureService()` — список окон и захват окна/экрана (Windows: GDI, mss).
- **dataset_config_builder** → `DatasetConfigBuilder()` — сборка объединённого `data.yaml` из нескольких датасетов.
- **project_root** → `PROJECT_ROOT` из `app.config`.

Все зависимости UI получают только **Container**; конкретные реализации интерфейсов (`ITrainer`, `IDetector`, `IWindowCapture`, `IDatasetConfigBuilder`) подставляются контейнером.

---

## 3. Интерфейсы (контракты)

**Файл:** `app/interfaces.py`

- **ITrainer**: `train(...)` — запуск обучения, возврат пути к `best.pt`; `stop()` — запрос остановки.
- **IDetector**: `load_model(weights_path)`, `predict(frame, conf, iou)` → `(annotated_frame, results)`, свойство `is_loaded`.
- **IWindowCapture**: `list_windows()` → `[(hwnd, title)]`, `capture_window(hwnd)`, `capture_primary_monitor()` — всё возвращает BGR numpy или None.
- **IDatasetConfigBuilder**: `build` / реализация с `build_multi` — объединение датасетов в один `data.yaml`.

Сервисы реализуют эти интерфейсы; UI зависит от интерфейсов, а не от конкретных классов.

---

## 4. Главное окно и оболочка

**Файл:** `app/ui/shell/main_window.py`

- **Центральный виджет:** горизонтальный layout: **сайдбар** + **QStackedWidget** (контент вкладок).
- **CollapsibleSidebar:** кнопки вкладок (`datasets`, `training`, `detection`, `integrations`), анимация сворачивания, сигнал `tab_changed`.
- **StackController** управляет стеком: для каждой вкладки сначала показывается placeholder «Загрузка…», при первом переключении на вкладку вызывается **фабрика** и подставляется реальный виджет (ленивая загрузка).
- Фабрики передаются из `main.py`: `TrainingView(container, signals)`, `DetectionView(container)`, `DatasetsView()`, `IntegrationsView()`.
- **CommandPalette** (Ctrl+K): быстрый переход по вкладкам и смена темы (light/dark).
- Горячие клавиши: Ctrl+1…4 — вкладки, Ctrl+K — палитра.
- При смене темы вызывается `refresh_theme()` у текущего виджета в стеке (если есть метод).
- При закрытии окна сохраняются геометрия, state и состояние сайдбара через **AppSettings**.

**Файл:** `app/ui/shell/stack_controller.py`

- `TAB_IDS = ("datasets", "training", "detection", "integrations")` — порядок совпадает с сайдбаром.
- `switch_to(tab_id)`: если виджет для вкладки ещё не создан — вызывается фабрика, placeholder заменяется на созданный виджет, затем показывается нужный индекс стека.

---

## 5. Настройки и тема

**Файл:** `app/ui/infrastructure/settings.py`

- **AppSettings** — обёртка над QSettings("YOLOStudio", "YOLO Desktop Studio").
- Хранит: геометрию/state главного окна, свёрнут ли сайдбар, имя темы (`"dark"` / `"light"`).
- `sync()` — сброс на диск.

**Файл:** `app/ui/theme/manager.py`

- **ThemeManager** — глобальный синглтон, при создании подменяет `_instance`.
- Хранит текущую тему, при `set_theme(name)` подставляет **TokenSet** (LIGHT/DARK), применяет палитру и глобальный стиль приложения, сохраняет тему в AppSettings и эмитит `theme_changed`.
- **Tokens** в `app/ui/theme/tokens.py` — цвета и отступы для виджетов (surface, text_primary, border, primary и т.д.).

---

## 6. Обучение: полный цикл

### 6.1. TrainingView (UI)

**Файл:** `app/ui/views/training/view.py`

- Строит форму: датасеты (несколько путей к папкам с `data.yaml` и train/valid), модель (комбо из YOLO_MODEL_CHOICES), эпохи, batch, imgsz, patience, workers, optimizer, проект (каталог runs), чекбоксы (удаление кэша и т.д.), кнопки «Старт» / «Стоп», прогресс-бар, таймеры, дашборд метрик (pyqtgraph), консольный лог (LogView).
- Хранит **TrainingViewModel** и подписывается на **TrainingSignals**.
- При «Старт»:
  - Собирает пути датасетов, проект, `combined_dir = project.parent / "combined_dataset"`, `out_yaml = combined_dir / "data.yaml"`.
  - Вызывает **container.dataset_config_builder.build_multi(dataset_paths, out_yaml)** — формируется один `data.yaml` с объединёнными train/val и классами.
  - Опционально удаляет `labels.cache` в датасетах.
  - Определяет модель (id из комбо или путь к .pt через scan_trained_weights).
  - Создаёт лог-файл в `project/logs/`.
  - Вызывает **view_model.start_training(...)** с параметрами (data_yaml, model_name, epochs, batch, imgsz, device, patience, project, weights_path, workers, optimizer, log_path, advanced_options).

### 6.2. TrainingViewModel (координация)

**Файл:** `app/ui/views/training/view_model.py`

- При **start_training** создаёт очередь `_console_queue`, при необходимости открывает лог-файл.
- В отдельном потоке вызывает **container.trainer.train(...)** с:
  - `on_progress` — эмитит `signals.progress_updated.emit(pct, msg)`;
  - `console_queue` — сюда пишется весь stdout/stderr обучения (редирект в TrainingService).
- По завершении потока: в очередь кладётся `None`, эмитится **signals.training_finished.emit(best_path, error)**.
- Таймер раз в ~80 ms опрашивает `_console_queue`, батчами эмитит **signals.console_lines_batch.emit(batch)** и пишет в лог-файл; при получении `None` останавливает таймер и закрывает лог.
- **stop_training()** вызывает **container.trainer.stop()** (устанавливает флаг остановки).

### 6.3. TrainingService (бизнес-логика обучения)

**Файл:** `app/services/training_service.py`

- **train()** в отдельном потоке (который ViewModel затем join'ит):
  - Редирект stdout/stderr в `console_queue`, чтобы весь вывод Ultralytics шёл в консоль UI.
  - Загрузка конфига интеграций: **Comet** (apply_comet_env), **Albumentations** (get_albumentations_transforms).
  - **YOLO(load_path)** — load_path это weights_path или model_name (например yolo11n.pt).
  - Регистрация колбэка **on_train_epoch_end**: проверка `_stop_requested` (кидает StopTrainingRequested), вызов `on_progress(current/total, "Epoch ...")`.
  - **model.train(data=..., epochs=..., batch=..., imgsz=..., device=..., patience=..., project=..., augmentations=..., advanced_options...)**. При несовместимости CUDA — повтор с device="cpu".
  - После успешного train: `best = Path(results.save_dir) / "weights" / "best.pt"`. Если файл есть — путь кладётся в result_holder.
  - **Явный экспорт в ONNX:** если `best.onnx` ещё нет — создаётся **YOLO(str(best))**, вызывается **export(format="onnx", imgsz=imgsz, dynamic=False, simplify=True, opset=12, half=False)**. Сообщения в console_queue; при ошибке экспорта обучение всё равно считается успешным.
  - `on_progress(1.0, "Training finished.")`.
  - В finally: восстановление stdout/stderr, restore_comet_env.
- По завершении потока **train()** возвращает путь к best.pt (или дефолтный путь к папке весов).

Обучение и экспорт ONNX выполняются в одном и том же потоке обучения; UI обновляется через сигналы и очередь лога.

---

## 7. Детекция: полный цикл

### 7.1. DetectionView (UI и потоки)

**Файл:** `app/ui/views/detection/view.py`

- Поля: модель (.pt или .onnx), источник (экран / окно / камера / видео), confidence, IOU, **вариант отрисовки** (OpenCV / D3DShot+PyTorch / ONNX), кнопки «Старт»/«Стоп», FPS, настройки вывода, фичи (Distance, Heatmap, ObjectCounter и т.д.).
- Конфиг визуализации загружается из **detection_visualization_config.json** (repository); выбранный backend_id определяет и способ отрисовки, и **какой детектор использовать**: при **backend_id == "onnx"** используется **container.detector_onnx**, иначе **container.detector**.
- При «Старт»:
  - Проверка пути к весам, conf/IOU, выбор источника (экран/окно/камера/видео). Для окна — проверка захвата тестовым кадром.
  - **Загрузка модели:** `_active_detector.load_model(Path(path))` (detector или detector_onnx в зависимости от backend_id).
  - Очистка очередей, создание бэкенда отрисовки: **get_backend(backend_id)**, **apply_settings(vis_config.get(backend_id, {}))**.
  - **backend.start_display(...)** — передаётся preview_queue (`_cv2_preview_queue`), max_w/max_h (PREVIEW_MAX_SIZE), getters для running и run_id, колбэки on_stop и on_q_key. Бэкенд в отдельном потоке читает из preview_queue и показывает кадры (imshow).
  - Запуск таймера FPS.
  - Для камеры/видео — поток **capture_loop**: в цикле `opencv_source.read()`, кадры кладутся в ** _frame_queue** (maxsize=1).
  - Для экрана/окна — **QTimer** с интервалом CAPTURE_INTERVAL_MS вызывает **_schedule_capture_frame**: при «Весь экран» — при наличии D3DShot у бэкенда вызывается **backend.capture_frame_fullscreen()**, иначе **window_capture.capture_primary_monitor()**; для окна — **window_capture.capture_window(hwnd)**. Кадр кладётся в _frame_queue.
  - Поток **inference_loop**: в цикле `frame = _frame_queue.get(timeout=...)`, затем **annotated, _ = _active_detector.predict(frame, conf, iou)**. При включённых Solutions (Heatmap, Counter и т.д.) к кадру применяются аннотаторы Ultralytics, результат перезаписывает annotated. Затем **_put_preview(annotated)**: в preview_queue кладётся **копия** кадра (numpy.copy() или torch.from_numpy(img.copy()).cuda() для D3DShot), чтобы поток отрисовки не делил буфер с следующим predict. Раз в секунду в _fps_queue кладётся FPS для обновления подписи.
- При «Стоп» или Q в окне превью: `_running = False`, остановка таймера захвата, **backend.stop_display()**, очистка очередей, сброс UI.

Итого три потока (кроме таймера): capture_loop (если камера/видео), inference_loop, display_loop (внутри бэкенда). Для экрана/окна вместо capture_loop используется таймер.

### 7.2. Детекторы (IDetector)

**Файл:** `app/yolo_inference/service.py` (DetectionService)

- **load_model(weights_path)** — только сохраняет путь; модель не создаётся в главном потоке.
- **predict(frame, conf, iou)** — в текущем потоке вызывается **_model()**: для этого потока в threading.local создаётся YOLO(str(_weights_path)), затем model.predict(source=frame, conf=..., iou=..., device=...). Результат: r.plot(), конвертация RGB→BGR, возврат (annotated, results). При ошибке CUDA — повтор с device="cpu" и установка _force_cpu.

**Файл:** `app/yolo_inference/onnx_detector.py` (OnnxDetectionService)

- **load_model(weights_path)**: если путь .onnx — используется он; если .pt — ожидается файл рядом с тем же именем и суффиксом .onnx; если его нет — вызывается **_export_pt_to_onnx(path)** (YOLO(str(path)).export(format="onnx", ...)). Создаётся **onnxruntime.InferenceSession** с провайдерами CUDA/DirectML/CoreML/CPU.
- **predict(frame, conf, iou)**: letterbox до 640×640, blob через cv2.dnn.blobFromImage, прогон session.run(), разбор выхода (N, 84), NMS через cv2.dnn.NMSBoxes, обратное масштабирование координат в исходный кадр, отрисовка боксов и подписей на копии кадра. Возврат (annotated, results).

Оба детектора возвращают BGR numpy (uint8), готовый для превью.

### 7.3. Захват экрана/окна (IWindowCapture)

**Файл:** `app/services/capture_service.py`

- **WindowCaptureService** при инициализации поднимает **pywin32** (win32gui, win32ui, win32con, win32api), при необходимости SetProcessDPIAware. **mss** инициализируется лениво в _ensure_mss (чтобы не тормозить старт).
- **list_windows()**: EnumWindows, видимые окна с непустым заголовком → список (hwnd, title).
- **capture_window(hwnd)**: для каждого hwnd кэшируется метод захвата. Порядок попыток: PrintWindow (PW_RENDERFULLCONTENT), PrintWindow(0), BitBlt, Redraw+PrintWindow; для свёрнутого окна — временно Restore → PrintWindow → Minimize. Если GDI не даёт контент — fallback на mss по региону окна. Возврат BGR numpy.
- **capture_primary_monitor()**: mss.grab(monitors[0]) или, при недоступности mss, GDI всего экрана. Конвертация в BGR numpy.

Камера и видео не входят в IWindowCapture: для них используется **OpenCVFrameSource** (cv2.VideoCapture) в том же view, с тем же интерфейсом read() → (ret, frame).

### 7.4. Визуализация детекции (бэкенды отрисовки)

**Файлы:**  
`app/features/detection_visualization/domain.py`, `backends/__init__.py`, `backends/base.py`, `opencv_backend.py`, `d3dshot_pytorch_backend.py`, `onnx_backend.py`, `repository.py`

- **Домен:** константы backend_id (opencv, d3dshot_pytorch, onnx), отображаемые имена, default_visualization_config() (секции opencv, d3dshot_pytorch, onnx с preview_max_w/h и флагами), встроенные пресеты.
- **Реестр бэкендов:** по backend_id создаётся экземпляр OpenCVBackend, D3DShotPyTorchBackend или OnnxBackend. **list_backends()** возвращает список (id, display_name) для комбобокса.
- **IVisualizationBackend:** get_id(), get_display_name(), get_default_settings(), get_settings(), apply_settings(settings), start_display(run_id, window_name, preview_queue, max_w, max_h, is_running_getter, run_id_getter, on_stop, on_q_key), stop_display(). Опционально: supports_d3dshot_capture(), capture_frame_fullscreen().
- **OpenCVBackend:** настройки из секции "opencv". start_display: в отдельном потоке цикл — get из preview_queue (с drain до последнего кадра), если кадр numpy uint8 HWC — ресайз через _resize_for_preview_opencv (cv2.cuda при наличии, иначе cv2.resize), np.ascontiguousarray, cv2.imshow. Окно "YOLO_%d" % run_id. По 'q' — on_q_key(). stop_display: флаг _running = False.
- **D3DShotPyTorchBackend:** настройки из "d3dshot_pytorch". supports_d3dshot_capture и capture_frame_fullscreen используют d3dshot при use_d3dshot_capture. start_display: поток отрисовки принимает и numpy, и torch-тензор из preview_queue; ресайз через PyTorch (GPU) или конвертация в numpy; imshow. Логика окна и 'q' аналогична.
- **OnnxBackend:** наследует OpenCVBackend, переопределяет get_id/get_display_name и _settings из секции "onnx". Отрисовка та же, что у OpenCV; инференс ONNX задаётся только выбором detector_onnx во view при backend_id == "onnx".
- **Repository:** load_visualization_config() / save_visualization_config() — JSON по DETECTION_VISUALIZATION_CONFIG_PATH, слияние с default при загрузке. Пресеты пользователя хранятся в том же JSON (presets).

Конфиг визуализации определяет, какой бэкенд отрисовки и какой детектор (PyTorch или ONNX) используются; выбор «Отрисовка: ONNX» в UI означает и бэкенд OnnxBackend, и детектор detector_onnx.

---

## 8. Датасеты и объединённый data.yaml

**Файл:** `app/services/dataset_service.py` (DatasetConfigBuilder)

- **build_multi(dataset_paths, output_yaml):** для каждой папки читается data.yaml, из всех собираются nc (максимум), names (объединение по индексам). Формируются списки путей train/val из каждой базы (поддержка train/valid/val и абсолютных/относительных путей). В итоговый data.yaml пишутся path, train, val, nc, names; файл сохраняется по output_yaml.
- **build(dataset1_path, dataset2_path, output_yaml, ...)** делегирует в build_multi([dataset1_path, dataset2_path], output_yaml).

**TrainingView** перед стартом обучения вызывает build_multi по выбранным датасетам и использует полученный `out_yaml` как единый data для model.train().

---

## 9. Интеграции и конфиг

**Файл:** `app/features/integrations_config.py`

- **default_config()** — словарь секций: albumentations, comet, dvc, sagemaker, kfold, tuning, model_export, sahi, seg_isolation, model_validation, ultralytics_solutions, detection_output.
- **load_config(path)** / **save_config(config, path)** — чтение/запись JSON по INTEGRATIONS_CONFIG_PATH (или переданному пути). При загрузке недостающие ключи подставляются из default.
- **export_config_to_file** — сохранение полного конфига в выбранный JSON (вкладка «Интеграции»).

Обучение и детекция читают этот конфиг: TrainingService — секции comet и albumentations; детекция — ultralytics_solutions (region, fps, colormap), detection_output (save_path, save_frames). Вкладка «Интеграции» (IntegrationsView) отображает формы для всех секций и сохраняет изменения через load_config/save_config.

---

## 10. Сигналы (мост потоки → UI)

**Файл:** `app/ui/infrastructure/signals.py`

- **TrainingSignals (QObject):** progress_updated(float, str), console_lines_batch(list), training_finished(best_path or None, error or None), training_stopped. Эмитируются из потоков ViewModel/Service; слоты выполняются в главном потоке Qt.
- **DetectionSignals:** fps_updated, detection_stopped — в текущей реализации детекция обновляет FPS и статус через очередь и таймер во view, не через эти сигналы.

---

## 11. Краткая схема потоков и данных

- **Главный поток Qt:** MainWindow, сайдбар, StackController, все View, палитра, тема, настройки. Обработка событий и слотов.
- **Поток обучения:** один поток в TrainingViewModel, в нём вызывается trainer.train(); stdout/stderr и on_progress уходят в очередь и сигналы; главный поток только читает очередь и обновляет UI.
- **Поток детекции — захват:** либо capture_loop (камера/видео), либо таймер в главном потоке (_schedule_capture_frame) для экрана/окна. Кадры → _frame_queue (maxsize=1).
- **Поток детекции — инференс:** inference_loop читает _frame_queue, вызывает _active_detector.predict(), при необходимости Solutions, кладёт копию кадра в _cv2_preview_queue, раз в секунду — FPS в _fps_queue.
- **Поток отрисовки:** внутри бэкенда (start_display) один поток читает _cv2_preview_queue, ресайз (если нужно) и cv2.imshow; по 'q' вызывается on_q_key → остановка детекции.

Очереди ограничены (maxsize=1 или 4), чтобы не накапливать задержку; при переполнении старый кадр заменяется новым (drop).

---

## 12. Конфигурационные файлы

- **QSettings** (платформа): геометрия окна, состояние сайдбара, тема.
- **integrations_config.json** (INTEGRATIONS_CONFIG_PATH): все интеграции и опции (Comet, Albumentations, K-Fold, Export, Solutions, detection_output и т.д.).
- **detection_visualization_config.json** (DETECTION_VISUALIZATION_CONFIG_PATH): backend_id, секции opencv, d3dshot_pytorch, onnx (preview_max_w/h, use_cuda_resize, use_d3dshot_capture), presets.

Загрузка при старте соответствующих экранов; сохранение при изменении настроек в UI.

---

Вся эта логика и даёт «детальную работу» приложения: от входа в main.py до потоков обучения и детекции, выбора детектора (PyTorch/ONNX) по бэкенду отрисовки, захвата экрана/окна/камеры/видео и отрисовки через выбранный бэкенд (OpenCV / D3DShot+PyTorch / ONNX).
