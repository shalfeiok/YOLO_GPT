# Гайды Ultralytics (секции J–M)

Краткое описание функций вкладки «Интеграции и мониторинг», реализованных по [документации Ultralytics](https://docs.ultralytics.com/ru/guides/).

## J. Изоляция объектов сегментации

**Модуль:** `app/features/segmentation_isolation/`

После predict сегментации (YOLO seg-модель) извлекаются контуры масок, строится бинарная маска, объект изолируется с чёрным или прозрачным фоном. Опционально — обрезка по ограничивающей рамке. Результаты сохраняются в PNG.

- **Конфиг:** `seg_isolation` — model_path, source_path (файл или папка), output_dir, background (black/transparent), crop.
- **Документация:** [Isolating Segmentation Objects](https://docs.ultralytics.com/ru/guides/isolating-segmentation-objects/).

## K. Валидация модели

**Модуль:** `app/features/model_validation/`

Запуск `model.val(data=data_yaml)` для оценки модели. В UI выводятся метрики: mAP50, mAP50–95, precision, recall, fitness.

- **Конфиг:** `model_validation` — data_yaml, weights_path.
- **Документация:** [Model Evaluation Insights](https://docs.ultralytics.com/ru/guides/model-evaluation-insights/).

## L. Ultralytics Solutions (видео)

**Модуль:** `app/features/ultralytics_solutions/`

Единый блок для работы с видео: выбор типа решения, путь к модели, источник (видео или камера «0»), выходной файл, регион (точки для счётчиков/зоны), FPS, colormap (для Heatmap). Сервис генерирует Python-скрипт с `ultralytics.solutions.*` и запускает его в subprocess (окна OpenCV не блокируют приложение).

Типы решений:

- **DistanceCalculation** — расчёт расстояния между выбранными объектами.
- **Heatmap** — тепловая карта по траекториям.
- **ObjectCounter** — подсчёт входа/выхода по линии или региону.
- **RegionCounter** — подсчёт по нескольким регионам.
- **SpeedEstimator** — оценка скорости объектов.
- **TrackZone** — отслеживание только в заданной зоне.

- **Конфиг:** `ultralytics_solutions` — solution_type, model_path, source, output_path, region_points, fps, colormap.
- **Документация:** [Distance](https://docs.ultralytics.com/ru/guides/distance-calculation/), [Heatmaps](https://docs.ultralytics.com/ru/guides/heatmaps/), [Object Counting](https://docs.ultralytics.com/ru/guides/object-counting/), [Region Counting](https://docs.ultralytics.com/ru/guides/region-counting/), [Speed Estimation](https://docs.ultralytics.com/ru/guides/speed-estimation/), [TrackZone](https://docs.ultralytics.com/ru/guides/trackzone/).

## M. Гайды: Streamlit, Custom Trainer

**Модуль:** `app/features/guides_launchers/`

- **Streamlit live inference** — по указанному пути к модели создаётся временный скрипт с `solutions.Inference(model=...).inference()` и запускается `streamlit run` в subprocess. Открывается браузер с инференсом в реальном времени.
- **Custom Trainer** — сохранение шаблона Python-файла с примером подкласса `DetectionTrainer` и переопределения `validate()` (например, для своих метрик).

- **Документация:** [Streamlit Live Inference](https://docs.ultralytics.com/ru/guides/streamlit-live-inference/), [Custom Trainer](https://docs.ultralytics.com/ru/guides/custom-trainer/).

## Секция E. Дополнительные гайды

Кнопки-ссылки на документацию по темам, для которых в приложении нет отдельной реализации:

- Model Monitoring & Maintenance  
- OpenVINO Optimization (latency vs throughput)  
- Preprocessing / Resizing  
- YOLO common issues (GPU)  
- Thread-safe inference  
- Solutions / SolutionAnnotator  
- Model YAML config  
- IBM Watsonx  

Экспорт в OpenVINO доступен в секции **H. Экспорт модели**; настройки latency/throughput см. в [документации OpenVINO](https://docs.ultralytics.com/ru/guides/optimizing-openvino-latency-vs-throughput-modes/).
