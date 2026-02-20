# Model Export

Экспорт весов YOLO в форматы развёртывания по [документации Ultralytics](https://docs.ultralytics.com/ru/guides/model-deployment-options/).

Поддерживаемые форматы: torchscript, onnx, openvino, engine (TensorRT), coreml, saved_model, pb (TensorFlow GraphDef), tflite, edgetpu, tfjs, paddle, ncnn.

Конфиг хранится в `integrations_config.json` (секция `model_export`).
