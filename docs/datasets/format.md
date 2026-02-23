# Формат датасета YOLO

Минимально ожидается:

```text
dataset/
  data.yaml
  images/
    train/
    val/
  labels/
    train/
    val/
```

## Пример `data.yaml`

```yaml
train: images/train
val: images/val
names: [cat, dog]
```

## Формат label строки

```text
<class_id> <x_center> <y_center> <width> <height>
```

Нормализация координат: значения от 0 до 1.
