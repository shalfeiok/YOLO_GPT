# Не изменять / Do not modify

Эта директория содержит реализацию **потокобезопасного инференса YOLO** по официальным рекомендациям Ultralytics:

- Экземпляр модели создаётся в том потоке, который вызывает `predict()` (thread-local).
- См. [Thread-Safe Inference with YOLO Models](https://docs.ultralytics.com/guides/yolo-thread-safe-inference).

**Файлы в этой директории не менять** — любые правки логики детекции делайте в `app/ui/detection_tab.py` или в обёртках в `app/services/`, не здесь.
