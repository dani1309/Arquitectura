"""Dimensionamiento (teoría de colas M/M/c) y costo diario del diseño propuesto."""
import math

ORDENES_DIA = 12_000_000
CHUNK = 5_000
MARGEN = 1.25

# Precios de lista us-east-1 (verificados oct-2026 en páginas oficiales salvo donde se indica)
LAMBDA_GBS_X86 = 0.0000166667
LAMBDA_GBS_ARM = 0.0000133334  # 20 % menos que x86 (no visible en la captura de la página)
LAMBDA_MEM_GB = 1.769           # 1.769 MB equivalen a 1 vCPU
LAMBDA_REQ = 0.20 / 1e6
FARGATE_VCPU_H = 0.0404784
FARGATE_GB_H = 0.004446
DDB_RRU = 0.125 / 1e6
DDB_WRU = 0.625 / 1e6
SQS_REQ = 0.40 / 1e6           # precio estándar conocido, no visible en la captura
S3_PUT = 0.005 / 1000
S3_GET = 0.0004 / 1000
S3_GB_MES = 0.023
ATHENA_TB = 5.0
APIGW_REST = 3.50 / 1e6
SFN_TRANS = 0.025 / 1000


def erlang_c(c: int, a: float) -> float:
    """Probabilidad de espera P(W>0) en M/M/c con carga ofrecida a = lambda/mu."""
    rho = a / c
    if rho >= 1:
        return 1.0
    s = sum(a**k / math.factorial(k) for k in range(c))
    top = a**c / math.factorial(c) / (1 - rho)
    return top / (s + top)


def dimensionar(lam_ordenes: float, k: float):
    lam = lam_ordenes / CHUNK          # chunks/s
    mu = k / CHUNK                     # chunks/s por worker
    a = lam / mu
    n = math.ceil(a * MARGEN)
    rho = a / n
    pw = erlang_c(n, a)
    wq = pw / (n * mu - lam)           # s
    lq = lam * wq                      # Little
    servicio = 1 / mu
    return dict(n=n, rho=rho, pw=pw, wq=wq, lq=lq, servicio=servicio,
                cap=n * k, drenaje_h=ORDENES_DIA / (n * k) / 3600)


print("=== Dimensionamiento M/M/c (chunk = 5.000 órdenes, margen 25 %) ===")
for nombre, ventana_h in [("24 h", 24), ("3 h", 3)]:
    lam = ORDENES_DIA / (ventana_h * 3600)
    print(f"\nVentana {nombre}: lambda = {lam:,.1f} órdenes/s")
    for k in (25, 100, 400):
        r = dimensionar(lam, k)
        print(f"  k={k:>3}/s/vCPU  N={r['n']:>3}  rho={r['rho']:.2f}  P(espera)={r['pw']:.3f}  "
              f"Wq={r['wq']:6.1f}s  Lq={r['lq']:.2f} chunks  servicio={r['servicio']:.0f}s  "
              f"capacidad={r['cap']:,}/s  drenaje={r['drenaje_h']:.2f} h")

print("\n=== Costo de cómputo por día (12M órdenes) ===")
for k in (25, 100, 400):
    vcpu_s = ORDENES_DIA / k
    lam_x86 = vcpu_s * LAMBDA_MEM_GB * LAMBDA_GBS_X86
    lam_arm = vcpu_s * LAMBDA_MEM_GB * LAMBDA_GBS_ARM
    farg = vcpu_s / 3600 * (FARGATE_VCPU_H + 2 * FARGATE_GB_H)
    print(f"  k={k:>3}: vCPU-h={vcpu_s/3600:7.1f}  Lambda x86=${lam_x86:6.2f}  Lambda Arm=${lam_arm:6.2f}  Fargate 1vCPU/2GB=${farg:6.2f}")

print("\n=== Costos por solicitudes y almacenamiento por día (k=100, Lambda Arm) ===")
lotes = ORDENES_DIA / 10_000
chunks = ORDENES_DIA / CHUNK
items = {
    "Cómputo Lambda Arm (k=100)": ORDENES_DIA / 100 * LAMBDA_MEM_GB * LAMBDA_GBS_ARM,
    "Invocaciones Lambda": (chunks + lotes * 3) * LAMBDA_REQ,
    "API Gateway REST (12 llamadas por lote)": lotes * 12 * APIGW_REST,
    "SQS (3 req por mensaje + sondeo largo)": ((lotes + chunks) * 3 + 2 * 5 * 86_400 / 20) * SQS_REQ,
    "S3 PUT/GET operativos": (lotes + 3 * chunks) * S3_PUT + (chunks * 2) * S3_GET,
    "DynamoDB padrón (BatchGet, 0,5 RRU/ítem)": ORDENES_DIA * 0.5 * DDB_RRU,
    "DynamoDB control de lotes (~4 WRU/chunk)": chunks * 4 * DDB_WRU,
    "Athena MERGE + OPTIMIZE (~5 GB/día)": 5 / 1024 * ATHENA_TB,
    "Step Functions (96 ejecuciones x 12 transiciones)": 96 * 12 * SFN_TRANS,
    "S3 almacenamiento incremental (18 GB/día, prorrateo mensual)": 18 * S3_GB_MES / 30,
}
total = 0
for k_, v in items.items():
    total += v
    print(f"  {k_:<62} ${v:8.4f}")
print(f"  {'TOTAL DÍA':<62} ${total:8.2f}")
print(f"  Costo por orden: ${total/ORDENES_DIA:.8f}  (por millón: ${total/ORDENES_DIA*1e6:.2f})")
print(f"  Mensual (30 días): ${total*30:,.0f}")

print("\n=== Sensibilidad del ahorro a la tasa de revisión manual ===")
MANUAL = 0.80  # línea base del RNF-03, pendiente de fuente
nube = total / ORDENES_DIA
for f in (0.02, 0.05, 0.10, 0.20, 0.30, 0.35):
    costo = nube + f * MANUAL
    print(f"  revisión manual {f:>4.0%}: costo efectivo ${costo:.4f}/orden  ahorro {1 - costo/MANUAL:.1%}")
print(f"  Umbral de f para ahorro >= 70 %: {0.30 - nube/MANUAL:.4f}")

print("\n=== Prototipo Learner Lab (1M órdenes) ===")
for k in (25, 100):
    for conc in (5, 10):
        t = 1_000_000 / (k * conc) / 60
        c = 1_000_000 / k * LAMBDA_MEM_GB * LAMBDA_GBS_ARM
        print(f"  k={k:>3}, concurrencia {conc:>2}: throughput {k*conc:>4}/s  tiempo {t:6.1f} min  cómputo ${c:.2f}")
