# Verificación temprana de permisos y servicios en el Learner Lab (R-01 · Tarea T2)

- **Fecha UTC:** 2026-11-11 23:17:44
- **Cuenta AWS:** `329771219583`
- **Identidad activa:** `arn:aws:sts::329771219583:assumed-role/voclabs/user5274396=daniel_lopez`
- **Región:** `us-east-1`

| Prueba R-01 | Servicio | Resultado | Evidencia / Decisión aplicada |
| :--- | :--- | :--- | :--- |
| Rol IAM LabRole | IAM | **OK** | ARN disponible: `arn:aws:iam::329771219583:role/LabRole` |
| S3 Object Lock (WORM) | S3 | **ALTERNATIVA_ACTIVA** | Se usa S3 Versioning + política DenyDelete + cadena SHA-256 (AccessDenied) |
| Amazon ECR | ECR | **OK** | Lectura de repositorios ECR permitida |
| Límite de concurrencia Lambda | Lambda | **OK** | ConcurrentExecutions=1000, Unreserved=1000 (worker usa MaximumConcurrency=10 en SQS) |
| Glue Data Catalog (T6 Iceberg) | Glue | **OK** | `glue:GetDatabases` disponible |
| Secrets Manager (clave HMAC) | Secrets Manager | **OK** | `list_secrets` permitido |
| Consulta de costo consumido | Cost Explorer | **OK** | API `ce:GetCostAndUsage` activa |

## Procedimiento de apagado y costo fijo cero (T2)

1. Todos los recursos aprovisionados (`S3`, `SQS`, `DynamoDB on-demand` y `AWS Lambda`) son 100 % serverless por uso y tienen **costo fijo de 0,00 USD/hora** en reposo.
2. Para desactivar completamente el consumo o limpiar el entorno al finalizar la sesión, ejecutar:
   ```bash
   python prototype/aws_learner_lab.py teardown
   ```
