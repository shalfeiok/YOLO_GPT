# Вывод детекции на GPU (ONNX)

## Универсальное поведение приложения

При загрузке ONNX-модели приложение:

1. **Windows:** подставляет в PATH каталог `…\CUDA\v12.x\bin` (или новее), если он есть в стандартной установке — чтобы подхватить CUDA без ручной настройки PATH.
2. Пытается создать сессию **только с GPU-провайдерами** (на Windows: DirectML → CUDA; на Linux: CUDA → ROCm; на macOS: CoreML).
3. Если не удалось — создаёт сессию с **CPU**.
4. В лог выводится фактический провайдер: `ONNX session created with providers: [...]`.

Чтобы реально работать на GPU, нужен соответствующий пакет и, для NVIDIA, установленные CUDA/cuDNN.

## Вариант без CUDA (Windows): DirectML

Если не хочешь ставить CUDA/cuDNN, на Windows можно использовать **DirectML** — ускорение на любой GPU (NVIDIA/AMD/Intel) без драйверов CUDA:

```bash
pip uninstall onnxruntime-gpu
pip install onnxruntime-directml
```

После этого при выборе отрисовки «ONNX» приложение само подхватит `DmlExecutionProvider` (на Windows он теперь проверяется первым). Перезапусти приложение.

## Вариант с CUDA (NVIDIA)

Установи **onnxruntime-gpu**, CUDA 12 и cuDNN 9. Приложение само добавит в PATH стандартный каталог CUDA (`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin`), если он есть — можно не добавлять его в систему вручную. Если cuDNN лежит не в папке CUDA, задай переменную окружения **CUDNN_PATH** или **CUDNN_HOME** на папку с cuDNN (в ней должна быть подпапка `bin`).

### Что уже сделано

- **onnxruntime-gpu** установлен в venv проекта (`pip install onnxruntime-gpu`).
- Через **winget** запущена установка **NVIDIA CUDA Toolkit** (если команда ещё выполняется — дождись окончания; установщик может предложить перезагрузку).

## Что нужно доделать вручную

### 1. cuDNN 9.x (обязательно для onnxruntime-gpu)

Пакет **cuDNN** через winget не ставится. Нужно:

1. Зайти на [NVIDIA cuDNN Archive](https://developer.nvidia.com/rdp/cudnn-archive).
2. Скачать **cuDNN 9.x для CUDA 12.x** (например, "cuDNN v9.x.x for CUDA 12.x" — Windows, ZIP или exe).
3. Распаковать архив и скопировать содержимое папок `bin`, `include`, `lib` в каталог установки CUDA (обычно `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x` или `v13.x`), либо добавить путь к папке **bin** cuDNN в переменную **PATH** (см. ниже).

### 2. PATH к DLL

Чтобы находились `cublasLt64_12.dll` и другие DLL:

- Добавь в **системную** переменную **PATH** (Параметры → Система → О программе → Дополнительные параметры системы → Переменные среды):
  - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin` (или `v13.x\bin`, если поставился CUDA 13)
  - Путь к папке **bin** из установки cuDNN (если копировал в CUDA — можно не добавлять).

Либо запускай приложение через **run_with_gpu.bat** — он временно добавляет эти пути в PATH и запускает приложение.

### 3. Если ошибка «cublasLt64_12.dll» остаётся

Текущий **onnxruntime-gpu** собран под **CUDA 12**. Если через winget установился только **CUDA 13**, в системе может быть `cublasLt64_13.dll`, а не `_12`. Варианты:

- Установить **CUDA 12** вручную с [NVIDIA CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-12-downloads-archive) и добавить его `bin` в PATH.
- Либо обновить **onnxruntime-gpu** до версии, которая поддерживает CUDA 13 (проверь [PyPI onnxruntime-gpu](https://pypi.org/project/onnxruntime-gpu/) и требования по CUDA).

## Копирование CUDA DLL в проект (без правки системы)

Чтобы не добавлять CUDA в системный PATH:

1. Запусти **`copy_cuda_to_project.bat`** из корня проекта (двойной щелчок в проводнике).  
   Скрипт копирует все DLL из `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin` в папку **`cuda_runtime\bin`**.
2. Запускай приложение через **`run_with_gpu.bat`** — он подставит `cuda_runtime\bin` в PATH и запустит `main_qt.py`.

Если CUDA установлена в другой каталог — открой `copy_cuda_to_project.bat` и измени переменную `SRC`.

## Ссылки

- [ONNX Runtime CUDA Execution Provider](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
- [Экспорт YOLO26 в ONNX (Ultralytics)](https://docs.ultralytics.com/ru/integrations/onnx/)
