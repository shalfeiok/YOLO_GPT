# YOLO Desktop Studio — UI Migration Roadmap

## 1. Анализ текущего UI (CustomTkinter)

### 1.1 Структура

| Компонент | Файл | Назначение |
|-----------|------|------------|
| Главное окно | `app/ui/main_window.py` | CTk, заголовок + CTkTabview, 4 вкладки |
| Обучение | `app/ui/training_tab.py` | Параметры, прогресс, метрики, консоль (CTkTextbox), системные метрики |
| Детекция | `app/ui/detection_tab.py` | Модель, источник (экран/окно/камера/видео), превью в отдельном окне OpenCV |
| Датасеты | `app/ui/datasets_tab.py` | VOC→YOLO, превью, аугментация, фильтры |
| Интеграции | `app/ui/integrations_tab.py` | Albumentations, Comet, DVC, SageMaker, визуализация |
| Тема | `app/ui/theme.py` | Палитра (light/dark), отступы, шрифты, карточки |

### 1.2 Потоки и контракты

- **Обучение**: UI создаёт `TrainingService()`, передаёт `on_progress: Callable[[float, str], None]` и `console_queue: Queue`. Обучение запускается в `Thread`; callback и `queue.put()` вызываются из фонового потока; UI обновляется через `self.after(0, lambda: ...)` и `after(80, _poll_console)`.
- **Детекция**: захват кадров (главный поток по таймеру для окно/экран, отдельный поток для камера/видео), инференс в отдельном потоке, превью в OpenCV `namedWindow` в потоке display backend.
- **Сервисы**: `app.services` — `DatasetConfigBuilder`, `TrainingService`, `DetectionService`, `WindowCaptureService`; интерфейсы в `app.interfaces` (ITrainer, IDetector, IWindowCapture, IDatasetConfigBuilder). **Менять нельзя.**

### 1.3 Ограничения CustomTkinter

- **Производительность**: CTkTextbox при 2k+ строках с частым `insert`/`delete` — тормоза; нет виртуализации списка.
- **Layout**: только grid/pack, нет QSplitter-подобного деления, нет docking.
- **Графики**: нет встроенного live-графика; метрики — одна строка текста + tooltip.
- **Тема**: переключение light/dark через `ctk.set_appearance_mode()` глобально; нет токенов и runtime switch без перезапуска виджетов.
- **Масштабирование**: нет нативного HiDPI/4K; один монолитный tab без lazy load.
- **Анимации**: почти нет (только прогресс-бар); нет плавных переходов, skeleton loaders, toast.

**Вывод**: для Enterprise-level ML Studio нужен переход на стек с нативным layout, виртуализацией, live-графиками и thread-safe сигналами.

---

## 2. Выбор стека (обоснование)

### 2.1 Варианты

| Критерий | CustomTkinter | PySide6 (Qt6) | Qt Quick/QML |
|----------|----------------|---------------|--------------|
| Производительность UI | Средняя | Высокая (C++ core) | Высокая |
| Live-графики | Нет | PyQtGraph | Qt Quick Charts / PyQtGraph |
| Docking | Нет | QDockWidget, QSplitter | Своя реализация |
| Thread safety | after() вручную | Сигналы/слоты (queued) | Сигналы |
| Виртуализация списка | Нет | QListView + QAbstractListModel | ListView + Model |
| Анимации | Нет | QPropertyAnimation, QVariantAnimation | Встроенные |
| 4K / HiDPI | Слабо | Нативная поддержка | Нативная |
| Зрелость для desktop | Средняя | Очень высокая | Выше для мобильного стиля |
| Сложность интеграции с существующим кодом | — | Прямые вызовы app.services | Тот же бэкенд, другой UI |

### 2.2 Решение: **PySide6 (Qt for Python 6)**

- **Производительность и масштабируемость**: нативный Qt Widgets, QSplitter, QDockWidget, сохранение layout в QSettings.
- **Live-графики**: **PyQtGraph** (совместим с PySide6) — `setData()` без полной перерисовки, zoom/pan, crosshair, 20–30 FPS для метрик.
- **Thread safety**: вызовы из worker в `QObject.emit()` с `Qt.ConnectionType.QueuedConnection` — доставка в главный поток без ручного `after`.
- **Логи**: `QAbstractListModel` + `QListView` с прокси-фильтром по уровню, ограничение буфера (100k+ строк с виртуализацией).
- **Тема**: `QPalette` + `ThemeManager` с токенами (Primary, Accent, Surface, …), переключение Dark/Light в runtime.
- **Детекция**: превью можно оставить в OpenCV-окне (как сейчас) или перенести в `QLabel`/`QGraphicsView` с QImage; resize-aware через `QResizeEvent` и ресайз буфера кадра.

**Qt Quick / QML** не выбираем как основной: для desktop-студии с формами, таблицами и docking виджеты дают быстрее результат и лучшую совместимость с PyQtGraph и QSettings; QML оставляем опцией для отдельных анимированных панелей позже.

### 2.3 Зависимости

- **PySide6** ≥ 6.6 — Qt 6 bindings, лицензия LGPL.
- **PyQtGraph** ≥ 0.13 — графики (опционально в Phase 1, обязательно с Phase 6).

---

## 3. Архитектурная схема (MVVM + Clean)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              View (Qt Widgets)                           │
│  MainWindow │ Sidebar │ QSplitter │ Dock(Logs) │ Dock(Metrics) │ Tabs     │
│  — только привязка к ViewModel, события → ViewModel, без вызова сервисов │
└─────────────────────────────────────────────────────────────────────────┘
                    ▲                              │
                    │ bindings                     │ user actions
                    │ (QProperty, signals)         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ViewModel (per view/screen)                      │
│  TrainingViewModel, DetectionViewModel, DatasetsViewModel, ...          │
│  — состояние экрана, команды (StartTraining, StopDetection), валидация  │
└─────────────────────────────────────────────────────────────────────────┘
                    ▲                              │
                    │ use cases                    │ calls
                    │                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Controller / Application (optional thin layer)         │
│  — запуск worker, подписка на консоль/прогресс, маппинг в ViewModel      │
└─────────────────────────────────────────────────────────────────────────┘
                    ▲                              │
                    │ inject                       │
                    │                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Domain & Services (НЕ ТРОГАТЬ)                                          │
│  app.interfaces.*  app.services.*  app.config  app.models  app.training_  │
│  metrics  app.console_redirect  Detection visualization backends         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Flow**: Worker (thread) → callback / queue → Controller или bridge → **сигнал Qt** → ViewModel обновляет свойства → View обновляется через binding или слоты.

**Правило**: View не вызывает `TrainingService.train()` напрямую; вызывает `ViewModel.start_training()`; ViewModel/Controller создаёт поток и передаёт в сервис `on_progress` и `console_queue`, затем эмитит сигналы для UI.

---

## 4. План реализации по фазам

### PHASE 1 – Infrastructure

| Пункт | Содержание |
|-------|------------|
| **Цель** | Запуск приложения на Qt, высокий DPI, мост поток→UI, DI для сервисов, сохранение окна через QSettings. |
| **Файлы** | `app/qt/__init__.py`, `app/qt/infrastructure/application.py`, `app/qt/infrastructure/signals.py`, `app/qt/infrastructure/di.py`, `app/qt/infrastructure/settings.py`, `main_qt.py` |
| **Зависимости** | PySide6, существующие app.config, app.interfaces, app.services |
| **Риски** | Конфликт с CustomTkinter при одном процессе — два entry point: `main.py` (CTk), `main_qt.py` (Qt). |
| **Acceptance criteria** | Запуск `python main_qt.py` открывает пустое главное окно Qt; геометрия сохраняется после перезапуска; из DI резолвятся TrainingService, DetectionService, WindowCaptureService, DatasetConfigBuilder. |

---

### PHASE 2 – AppShell

| Пункт | Содержание |
|-------|------------|
| **Цель** | Collapsible sidebar (иконки + tooltip), QStackedWidget для контента, lazy load вкладок, клавиатурная навигация, анимация ширины сайдбара. |
| **Файлы** | `app/qt/shell/main_window.py`, `app/qt/shell/sidebar.py`, `app/qt/shell/stack_controller.py` |
| **Зависимости** | Phase 1 |
| **Риски** | Нет |
| **Acceptance criteria** | Сайдбар сворачивается/разворачивается с анимацией; переключение вкладок по клику и с клавиатуры; контент вкладок создаётся при первом показе. |

---

### PHASE 3 – Component library

| Пункт | Содержание |
|-------|------------|
| **Цель** | Карточки параметров, кнопки (primary/secondary), поля ввода с валидацией, tooltips, скелетоны, тосты, диалоги подтверждения. |
| **Файлы** | `app/qt/components/cards.py`, `app/qt/components/buttons.py`, `app/qt/components/inputs.py`, `app/qt/components/toast.py`, `app/qt/components/skeleton.py` |
| **Зависимости** | Phase 1, ThemeManager (базовые токены из Phase 8 можно заложить раньше) |
| **Риски** | Нет |
| **Acceptance criteria** | Единый вид кнопок/карточек/полей; toast показывается и скрывается; подтверждение «Остановить обучение?» через общий диалог. |

---

### PHASE 4 – Training View

| Пункт | Содержание |
|-------|------------|
| **Цель** | Панель параметров (датасеты, модель, эпохи, batch, imgsz, patience, runs dir), панель метрик в реальном времени, системный монитор, прогресс с анимацией, кнопки Старт/Стоп, отмена с подтверждением, overlay загрузки. |
| **Файлы** | `app/qt/views/training/view.py`, `app/qt/views/training/view_model.py`, `app/qt/views/training/controller.py` (или логика в ViewModel + bridge сигналов) |
| **Зависимости** | Phase 1–3, app.services.TrainingService, app.training_metrics, app.console_redirect |
| **Риски** | Сохранить точный контракт train(..., on_progress, console_queue, workers, optimizer, weights_path). |
| **Acceptance criteria** | Запуск/остановка обучения как в текущем приложении; прогресс и метрики обновляются без блокировки UI; консоль выводит строки из очереди (до Phase 7 — простой QPlainTextEdit или список). |

---

### PHASE 5 – Detection View

| Пункт | Содержание |
|-------|------------|
| **Цель** | Выбор модели, источник (экран/окно/камера/видео), confidence/IOU, контейнер превью (или ссылка на OpenCV окно), FPS, fullscreen, монитор производительности. |
| **Файлы** | `app/qt/views/detection/view.py`, `app/qt/views/detection/view_model.py`, интеграция с app.features.detection_visualization |
| **Зависимости** | Phase 1–3, DetectionService, WindowCaptureService, OpenCVFrameSource |
| **Риски** | Потоки capture/inference/display не менять; только UI перевести на Qt. |
| **Acceptance criteria** | Старт/стоп детекции; смена источника и параметров; FPS и превью работают как сейчас. |

---

### PHASE 6 – Metrics Dashboard

| Пункт | Содержание |
|-------|------------|
| **Цель** | Графики PyQtGraph: streaming (setData), zoom/pan, crosshair, значения по hover, overlay нескольких запусков, экспорт. |
| **Файлы** | `app/qt/views/metrics/dashboard.py`, `app/qt/views/metrics/plot_model.py` |
| **Зависимости** | Phase 1, 4, PyQtGraph |
| **Риски** | Обновления с частотой 20–30 FPS, батчинг точек. |
| **Acceptance criteria** | Во время обучения кривые loss/метрик обновляются в реальном времени без полной перерисовки; zoom/pan и crosshair работают. |

---

### PHASE 7 – Log System

| Пункт | Содержание |
|-------|------------|
| **Цель** | QAbstractListModel + QListView, виртуализация, лимит буфера (например 100k строк), умный auto-scroll, фильтр по уровню (INFO/WARN/ERROR). |
| **Файлы** | `app/qt/components/log_model.py`, `app/qt/components/log_view.py`, интеграция с TrainingViewModel (консоль обучения) и глобальным логом приложения. |
| **Зависимости** | Phase 1, 4 |
| **Риски** | Производительность при очень частых вставках — батчинг по таймеру. |
| **Acceptance criteria** | 100k+ строк без подвисаний; фильтр по уровню; автоскролл при новом сообщении, если пользователь внизу. |

---

### PHASE 8 – Theme System

| Пункт | Содержание |
|-------|------------|
| **Цель** | ThemeManager с токенами (Primary, Accent, Background, Surface, TextPrimary, TextSecondary, Success, Warning, Error), Dark/Light, переключение в runtime. |
| **Файлы** | `app/qt/theme/manager.py`, `app/qt/theme/tokens.py`, применение к QPalette и к стилям виджетов. |
| **Зависимости** | Phase 1 |
| **Риски** | Нет |
| **Acceptance criteria** | Переключение темы меняет все основные экраны без перезапуска. |

---

### PHASE 9 – Performance Optimization

| Пункт | Содержание |
|-------|------------|
| **Цель** | Batched metric updates, debounce UI signals, lazy init views, отсутствие full repaint графиков, проверка на 4K. |
| **Файлы** | Все view/viewmodel, infrastructure/signals (batch emit) |
| **Зависимости** | Phases 1–8 |
| **Риски** | Нет |
| **Acceptance criteria** | UI не блокируется при обучении; графики 20–30 FPS; приложение читаемо на 4K. |

---

### PHASE 10 – Polishing & UX

| Пункт | Содержание |
|-------|------------|
| **Цель** | Hover/fade/slide анимации, micro-interactions, тосты, inline validation, горячие клавиши, command palette, skeleton loaders, disabled states. |
| **Файлы** | Компоненты, shell, глобальные шорткаты и CommandPalette виджет |
| **Зависимости** | Phases 1–9 |
| **Риски** | Нет |
| **Acceptance criteria** | Соответствие списку UX из ТЗ (tooltips, confirmations, shortcuts, command palette). |

---

## 5. Отслеживание прогресса

- [x] **Phase 1 – Infrastructure** — Completed
- [x] **Phase 2 – AppShell** — Completed
- [x] **Phase 3 – Component library** — Completed
- [x] **Phase 4 – Training View** — Completed
- [x] **Phase 5 – Detection View** — Completed
- [x] **Phase 6 – Metrics Dashboard** — Completed
- [x] **Phase 7 – Log System** — Completed
- [x] **Phase 8 – Theme System** — Completed
- [x] **Phase 9 – Performance Optimization** — Completed
- [x] **Phase 10 – Polishing & UX** — Completed

После завершения фазы помечать: `[x] Phase N – Completed`.

---

## 6. Критерии качества (на весь проект)

- Production-ready: стабильный запуск, сохранение настроек, корректное завершение потоков.
- Масштабируемость: добавление новой вкладки/виджета без ломки архитектуры.
- Thread-safe: все обновления UI только через Qt signals из главного потока.
- Чистая архитектура: View не знает о сервисах; только ViewModel/Controller.
- Расширяемость: новые токены темы, новые панели в dock.
- Быстрее текущего UI: логи 100k строк, графики без лагов.
- Современный и enterprise-grade вид и поведение.
