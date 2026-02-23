# Артефакты обучения (runs)

Типовая структура:

```text
runs/
  train/
    exp*/
      args.yaml
      results.csv
      weights/
        best.pt
        last.pt
      events.out.tfevents...
```

## Что где смотреть
- `results.csv` — динамика метрик по эпохам.
- `args.yaml` / `opt.yaml` — фактические параметры запуска.
- `weights/best.pt` — лучшая модель для инференса.

`RunArtifactsReader` умеет читать эти файлы и возвращать warnings при отсутствии частей артефактов.
