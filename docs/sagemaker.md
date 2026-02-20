# Интеграция Amazon SageMaker

Официальный гайд: [Ultralytics — Amazon SageMaker](https://docs.ultralytics.com/ru/integrations/amazon-sagemaker/).

## Назначение

Amazon SageMaker — управляемый сервис для масштабируемого инференса. Развёртывание через AWS CDK обеспечивает воспроизводимую инфраструктуру для моделей YOLO.

## Требования

- Учётная запись AWS.
- Настроенные IAM-роли с правами на SageMaker, CloudFormation, S3.
- Установленный и настроенный [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- Установленный [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/#getting-started_install).
- Достаточные квоты на инстансы (например, `ml.m5.4xlarge`).

## Использование в приложении

1. Вкладка **«Интеграции и мониторинг»** → секция **D. Облачный деплой (Amazon SageMaker)**.
2. Нажмите **«Клонировать шаблон SageMaker»** — в папку проекта клонируется репозиторий [host-yolov8-on-sagemaker-endpoint](https://github.com/aws-samples/host-yolov8-on-sagemaker-endpoint).
3. Укажите **Instance type** (по умолчанию `ml.m5.4xlarge`), **Название endpoint**, **Путь к модели (.pt)**.
4. Нажмите **«Развернуть через CDK»** — в фоне выполнится `cdk deploy` в каталоге шаблона; лог выводится в текстовое поле. Развёртывание может занять несколько минут.
5. **«Очистить endpoint»** — напоминание выполнить очистку в консоли AWS или через `cdk destroy` для экономии средств.

## Дополнительно

После развёртывания тестирование и мониторинг выполняются через консоль AWS SageMaker и приложенные в шаблоне Jupyter-ноутбуки (см. официальный гайд Ultralytics и репозиторий aws-samples).
