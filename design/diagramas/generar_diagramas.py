"""Genera los diagramas de arquitectura (C4 niveles 1 a 3 y vista de despliegue en AWS).

Requisitos:  pip install diagrams   y Graphviz instalado (comando `dot`).
Uso:         python generar_diagramas.py      (escribe los PNG en esta misma carpeta)
"""
from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import Athena, GlueDataCatalog
from diagrams.aws.compute import EC2ContainerRegistry, Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.general import Users
from diagrams.aws.integration import Eventbridge, SimpleQueueServiceSqs, StepFunctions
from diagrams.aws.management import Cloudwatch, CloudwatchAlarm
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager
from diagrams.aws.storage import SimpleStorageServiceS3Bucket
from diagrams.c4 import C4Node, Container, Database, Person, Relationship, System, SystemBoundary

SALIDA = Path(__file__).resolve().parent
FUENTE = "Inter"
GRAFO = {"fontname": FUENTE, "fontsize": "22", "pad": "0.4", "nodesep": "0.6", "ranksep": "1.0"}
NODO = {"fontname": FUENTE}
ARISTA = {"fontname": FUENTE, "fontsize": "11"}
TAM = {"width": "3.4", "height": "1.7"}
GRIS = {"fillcolor": "gray55"}
LIBRE = {"constraint": "false"}  # la arista se dibuja pero no condiciona el orden de columnas


def rel(texto: str, **extra) -> Relationship:
    return Relationship(texto, **extra)


def componente(nombre: str, tecnologia: str, descripcion: str):
    """Nodo C4 de nivel 3 (Component) en azul claro, según la convención C4."""
    return C4Node(nombre, tecnologia, descripcion, type="Component",
                  fillcolor="#85BBF0", fontcolor="black", **TAM)


def c4_contexto() -> None:
    with Diagram("C4 Nivel 1 · Contexto del sistema", filename=str(SALIDA / "c4_1_contexto"), show=False,
                 direction="TB", graph_attr=dict(GRAFO, splines="spline"), node_attr=NODO, edge_attr=ARISTA):
        ips = Person("Entidad emisora (IPS)", "Radica lotes CSV de órdenes médicas y consulta su estado", **TAM)
        auditor = Person("Auditor médico", "Revisa órdenes marcadas con incertidumbre clínica", **TAM)
        analista = Person("Analista del pagador", "Consulta adjudicaciones y prepara los giros", **TAM)
        control = Person("Ente de control", "Verifica la integridad de cualquier decisión", **TAM)

        sistema = System("SAOM · Chernovia", "Sistema de Adjudicación de Órdenes Médicas COIL. Valida, extrae, "
                         "dictamina, liquida y deja evidencia inmutable", width="4.2", height="1.9")

        padron = System("Catálogo de perfiles COIL", "PRIORITARIO (100 %), ESTANDAR (50 %), COPAGO (25 %)",
                        external=True, **TAM, **GRIS)
        catalogo = System("Catálogo de servicios (COV-001..020)", "Servicios cubiertos, medicaciones y rangos de referencia",
                          external=True, **TAM, **GRIS)
        tesoreria = System("Tesorería del pagador", "Ejecuta los giros a las entidades emisoras", external=True, **TAM, **GRIS)

        ips >> rel("Radica lotes CSV y consulta estado [HTTPS]") >> sistema
        auditor >> rel("Revisa casos marcados") >> sistema
        analista >> rel("Consulta adjudicaciones [SQL]") >> sistema
        control >> rel("Verifica recibos y hashes") >> sistema
        sistema >> rel("Importa perfiles de cobertura") >> padron
        sistema >> rel("Importa catálogo de servicios cubiertos") >> catalogo
        sistema >> rel("Entrega liquidaciones") >> tesoreria


def c4_contenedores() -> None:
    with Diagram("C4 Nivel 2 · Contenedores", filename=str(SALIDA / "c4_2_contenedores"), show=False,
                 direction="TB", graph_attr=dict(GRAFO, splines="spline", ranksep="0.8", nodesep="0.5"), node_attr=NODO, edge_attr=ARISTA):
        ips = Person("Entidad emisora (IPS)", **TAM)
        usuarios = Person("Usuarios del pagador", "Analistas, auditores y entes de control", **TAM)

        with SystemBoundary("SAOM · Chernovia (AWS us-east-1)"):
            api = Container("API de radicación", "API Gateway REST + Lambda",
                            "Crea lotes, entrega URL prefirmada y expone el estado", **TAM)
            raw = Database("Zona raw con PII", "S3, SSE-KMS",
                           "Archivos CSV originales (COIL); acceso restringido", **TAM)
            q_lotes = Container("Cola lotes-recibidos", "SQS estándar", "Desacopla la llegada de archivos", **TAM)
            particionador = Container("Particionador", "Lambda Python",
                                      "Valida el CSV y lo divide en chunks de 5.000 órdenes", **TAM)
            q_chunks = Container("Cola chunks-adjudicacion", "SQS estándar + DLQ",
                                 "Reparte el trabajo entre workers (coordinador)", **TAM)
            adjudicador = Container("Workers de adjudicación", "Lambda, imagen de contenedor Arm",
                                    "Pseudonimiza, extrae, dictamina, liquida y firma cada orden", **TAM)
            control = Database("Control de lotes", "DynamoDB on-demand",
                               "Estado e idempotencia por lote y chunk (control_lotes)", **TAM)
            ref = Database("Referencias COIL", "S3 versionado",
                           "COIL_catalogo_servicios_cubiertos.csv y COIL_catalogo_perfiles_cobertura.csv", **TAM)
            curated = Database("Adjudicaciones", "Iceberg en S3 + Glue Catalog",
                               "Tabla analítica particionada por día de radicación", **TAM)
            audit = Database("Recibos de auditoría", "S3 Object Lock (WORM)",
                             "Recibos por orden y raíz hash por chunk y lote", **TAM)
            consolidador = Container("Consolidador", "Scheduler + Step Functions + Athena",
                                     "MERGE a Iceberg cada 15 min; OPTIMIZE diario", **TAM)
            obs = Container("Observabilidad", "CloudWatch",
                            "Logs sin PII, métricas EMF, alarmas de DLQ y edad de cola", **TAM)

        ips >> rel("1 POST /lotes") >> api
        api >> rel("registra lote") >> control
        ips >> rel("2 PUT archivo CSV (URL prefirmada)") >> raw
        raw >> rel("3 evento ObjectCreated") >> q_lotes
        q_lotes >> rel("4") >> particionador
        particionador >> rel("5 descriptores de chunk") >> q_chunks
        q_chunks >> rel("6 un mensaje por invocación") >> adjudicador
        adjudicador >> rel("lee rango de bytes", **LIBRE) >> raw
        adjudicador >> rel("7 idempotencia y estado") >> control
        adjudicador >> rel("catálogos vigentes") >> ref
        adjudicador >> rel("8 Parquet en staging") >> curated
        adjudicador >> rel("9 recibos firmados") >> audit
        adjudicador >> rel("logs y métricas") >> obs
        curated << rel("10 MERGE INTO") << consolidador
        consolidador << rel("11 consultas SQL") << usuarios


def c4_componentes() -> None:
    with Diagram("C4 Nivel 3 · Componentes del worker de adjudicación", filename=str(SALIDA / "c4_3_componentes"),
                 show=False, direction="LR", graph_attr=dict(GRAFO, ranksep="0.8"), node_attr=NODO, edge_attr=ARISTA):
        cola = Container("Cola chunks-adjudicacion", "SQS", **TAM, **GRIS)
        with SystemBoundary("Worker de adjudicación (Lambda)"):
            with SystemBoundary("Preparación"):
                lector = componente("Lector y validador", "Python, csv + pydantic",
                                    "Lee el rango CSV del chunk y valida el esquema de cada orden (RF-01)")
                pseudo = componente("Pseudonimizador", "HMAC-SHA256 + enmascarador #",
                                    "Crea patient_token y enmascara Paciente, DNO y SeguroSocial conservando longitud")
                ner = componente("Extractor clínico", "Parser / NER con spans",
                                 "Edad, PerfilCobertura, ServicioSolicitado y Medicacion con spans (RF-02)")
                perfil = componente("Resolutor de perfil", "Catálogo COIL en memoria (o padrón DDB)",
                                    "Mapea PRIORITARIO (100%), ESTANDAR (50%), COPAGO (25%)")
            with SystemBoundary("Decisión y evidencia"):
                reglas = componente("Motor de cobertura", "Catálogo COV-001..COV-020",
                                    "CUBRE o NO_CUBRE con código de servicio y versión (RF-03)")
                liquidador = componente("Liquidador", "Decimal, ROUND_HALF_UP",
                                        "Aplica 100, 50, 25 o 0 por ciento (RF-04)")
                firmador = componente("Generador de recibo", "JSON canónico + SHA-256",
                                      "Hash por orden y raíz del chunk (RF-05)")
                escritor = componente("Escritor idempotente", "PyArrow, boto3",
                                      "Claves deterministas y escritura condicional")
        secretos = Database("Clave HMAC", "Secrets Manager", **GRIS)
        padron = Database("Control / Padrón", "DynamoDB", **GRIS)
        catalogo = Database("Catálogos COIL", "S3 ref", **GRIS)
        salidas = Database("Staging, recibos y control", "S3 + DynamoDB", **TAM, **GRIS)

        cola >> lector >> pseudo >> ner >> perfil
        cola >> Edge(style="invis") >> reglas  # segunda fila alineada bajo la primera
        perfil >> Relationship("orden enriquecida", constraint="false") >> reglas
        reglas >> liquidador >> firmador >> escritor >> salidas
        pseudo >> rel("clave en caché") >> secretos
        perfil >> rel("catálogo o padrón") >> padron
        reglas >> rel("cargado al iniciar", **LIBRE) >> catalogo


def aws_flujo() -> None:
    grafo = dict(GRAFO, ranksep="1.2", nodesep="0.5", splines="spline")
    paso = lambda n, txt="": Edge(label=f"{n} {txt}".strip(), fontname=FUENTE, fontsize="12", color="#232F3E")
    aux = lambda txt="", **kw: Edge(label=txt, fontname=FUENTE, fontsize="10", style="dashed", color="gray45", **kw)
    with Diagram("Flujo en AWS · Ingesta continua y adjudicación en micro-lotes", filename=str(SALIDA / "aws_flujo"),
                 show=False, direction="LR", graph_attr=grafo, node_attr=NODO, edge_attr=ARISTA):
        ips = Users("Entidades emisoras\n(IPS)")

        with Cluster("AWS us-east-1 · servicios regionales replicados en varias AZ"):
            with Cluster("Ingesta"):
                api = APIGateway("API Gateway REST\nAPI key y cuotas")
                fn_api = Lambda("radicacion-api")
                raw = SimpleStorageServiceS3Bucket("S3 raw\nCSV con PII, SSE-KMS")
                q_lotes = SimpleQueueServiceSqs("SQS\nlotes-recibidos")
                fn_part = Lambda("particionador")

            with Cluster("Procesamiento distribuido"):
                q_chunks = SimpleQueueServiceSqs("SQS\nchunks-adjudicacion")
                workers = Lambda("adjudicador x N\nconcurrencia máxima")
                dlq = SimpleQueueServiceSqs("DLQ")
                ecr = EC2ContainerRegistry("ECR\nimagen y modelo")
                secretos = SecretsManager("Secrets Manager\nclave HMAC")

            with Cluster("Almacenamiento distribuido"):
                ddb = Dynamodb("DynamoDB\ncontrol_lotes")
                ref = SimpleStorageServiceS3Bucket("S3 ref\ncatálogos COIL")
                curated = SimpleStorageServiceS3Bucket("S3 curated\nstaging + Iceberg")
                audit = SimpleStorageServiceS3Bucket("S3 audit\nObject Lock WORM")

            with Cluster("Consolidación y consulta"):
                athena = Athena("Athena\nMERGE, OPTIMIZE, SQL")
                glue = GlueDataCatalog("Glue Data Catalog")
                sfn = StepFunctions("Step Functions\ncierre de micro-lote")
                sched = Eventbridge("EventBridge Scheduler\ncada 15 min")

            with Cluster("Observabilidad"):
                cw = Cloudwatch("CloudWatch\nlogs y métricas EMF")
                alarmas = CloudwatchAlarm("Alarmas\nDLQ, edad de cola, costo")

        usuarios = Users("Analistas, auditores\ny entes de control")

        # Camino principal (numerado como en la tabla de flujo del documento)
        ips >> paso(1, "POST /lotes") >> api >> fn_api
        fn_api >> aux("crea lote") >> ddb
        ips >> paso(2, "PUT archivo CSV") >> raw
        raw >> paso(3, "evento") >> q_lotes >> paso(4) >> fn_part
        fn_part >> paso(5, "descriptores") >> q_chunks >> paso(6) >> workers
        workers >> paso(7, "estado chunk") >> ddb
        workers >> paso(8, "Parquet") >> curated
        workers >> paso(9, "recibos") >> audit
        curated << paso(10, "MERGE INTO") << athena << paso("") << sfn << paso("") << sched
        athena << paso(11, "SQL") << usuarios

        # Dependencias auxiliares (no fijan el orden de columnas)
        q_chunks >> aux("3 reintentos fallidos", constraint="false") >> dlq
        ecr >> aux("imagen", constraint="false") >> workers
        workers >> aux("clave", constraint="false") >> secretos
        workers >> aux("lee rango", constraint="false") >> raw
        workers >> aux() >> ref
        athena >> aux("esquema", constraint="false") >> glue
        workers >> aux() >> cw >> aux() >> alarmas


if __name__ == "__main__":
    c4_contexto()
    c4_contenedores()
    c4_componentes()
    aws_flujo()
    print("Diagramas generados en", SALIDA)
