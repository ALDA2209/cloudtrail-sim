import random
from datetime import timedelta

from django.utils import timezone

from .models import Evento

USUARIOS = ["admin", "aldahir.silva", "juan.perez", "maria.lopez", "dev.backend", "auditor"]
IPS = ["190.117.45.12", "181.65.23.10", "200.48.225.130", "179.6.12.88", "10.0.1.25"]
IP_ATACANTE = "185.220.101.34"
REGIONES = ["us-east-1", "us-west-2", "sa-east-1"]
USER_AGENTS = [
    "console.amazonaws.com",
    "aws-cli/2.15.30 Python/3.11.8 Linux/5.15",
    "Boto3/1.34.69 Python/3.12.2 Windows/10",
]
UA_NAVEGADOR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"


def _bucket():
    return f"empresa-{random.choice(['datos', 'backups', 'logs', 'reportes'])}-{random.randint(100, 999)}"


def _instancia():
    return "i-0" + "".join(random.choices("0123456789abcdef", k=16))


ACCIONES = {
    "ConsoleLogin": {
        "servicio": "Consola", "source": "signin.amazonaws.com", "tipo": "AwsConsoleSignIn",
        "read_only": False, "desc": "Iniciar sesión en la consola",
        "params": None,
        "error": ("Failed authentication", "Failed authentication"),
    },
    "ListBuckets": {
        "servicio": "S3", "source": "s3.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": True, "desc": "Listar buckets",
        "params": None,
        "error": ("AccessDenied", "Access Denied"),
    },
    "CreateBucket": {
        "servicio": "S3", "source": "s3.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Crear bucket",
        "params": lambda: {"bucketName": _bucket()},
        "error": ("BucketAlreadyExists", "The requested bucket name is not available."),
    },
    "DeleteBucket": {
        "servicio": "S3", "source": "s3.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Eliminar bucket",
        "params": lambda: {"bucketName": _bucket()},
        "error": ("AccessDenied", "Access Denied"),
    },
    "DescribeInstances": {
        "servicio": "EC2", "source": "ec2.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": True, "desc": "Consultar instancias",
        "params": None,
        "error": ("UnauthorizedOperation", "You are not authorized to perform this operation."),
    },
    "RunInstances": {
        "servicio": "EC2", "source": "ec2.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Crear instancia (servidor)",
        "params": lambda: {"instanceType": random.choice(["t2.micro", "t3.medium", "m5.large"]),
                           "imageId": "ami-0c55b159cbfafe1f0", "minCount": 1, "maxCount": 1},
        "error": ("UnauthorizedOperation", "You are not authorized to perform this operation."),
    },
    "TerminateInstances": {
        "servicio": "EC2", "source": "ec2.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Eliminar instancia (servidor)",
        "params": lambda: {"instancesSet": {"items": [{"instanceId": _instancia()}]}},
        "error": ("InvalidInstanceID.NotFound", "The instance ID does not exist."),
    },
    "AuthorizeSecurityGroupIngress": {
        "servicio": "EC2", "source": "ec2.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Abrir puerto 22 a internet",
        "params": lambda: {"groupId": "sg-0a1b2c3d4e5f", "ipPermissions": {"items": [
            {"ipProtocol": "tcp", "fromPort": 22, "toPort": 22,
             "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]}}]}},
        "error": ("UnauthorizedOperation", "You are not authorized to perform this operation."),
    },
    "CreateUser": {
        "servicio": "IAM", "source": "iam.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Crear usuario IAM",
        "params": lambda: {"userName": f"usuario{random.randint(10, 99)}"},
        "error": ("AccessDenied", "User is not authorized to perform iam:CreateUser"),
    },
    "DeleteUser": {
        "servicio": "IAM", "source": "iam.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Eliminar usuario IAM",
        "params": lambda: {"userName": f"usuario{random.randint(10, 99)}"},
        "error": ("NoSuchEntity", "The user cannot be found."),
    },
    "AttachUserPolicy": {
        "servicio": "IAM", "source": "iam.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Dar permisos de administrador",
        "params": lambda: {"userName": random.choice(USUARIOS),
                           "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"},
        "error": ("AccessDenied", "User is not authorized to perform iam:AttachUserPolicy"),
    },
    "StopLogging": {
        "servicio": "CloudTrail", "source": "cloudtrail.amazonaws.com", "tipo": "AwsApiCall",
        "read_only": False, "desc": "Apagar CloudTrail",
        "params": lambda: {"name": "arn:aws:cloudtrail:us-east-1:123456789012:trail/trail-principal"},
        "error": ("AccessDenied", "User is not authorized to perform cloudtrail:StopLogging"),
    },
}


def registrar_evento(accion, usuario, ip, region="us-east-1", fallar=False,
                     user_agent=None, event_time=None, params=None):
    """Simula que CloudTrail captura una llamada a la API de AWS."""
    cfg = ACCIONES[accion]
    if params is None and cfg["params"]:
        params = cfg["params"]()
    if user_agent is None:
        user_agent = UA_NAVEGADOR if cfg["tipo"] == "AwsConsoleSignIn" else "console.amazonaws.com"

    error_code, error_message = cfg["error"] if fallar else ("", "")

    return Evento.objects.create(
        event_time=event_time or timezone.now(),
        event_name=accion,
        event_source=cfg["source"],
        event_type=cfg["tipo"],
        read_only=cfg["read_only"],
        user_name=usuario,
        source_ip=ip,
        aws_region=region,
        user_agent=user_agent,
        request_parameters=params,
        error_code=error_code,
        error_message=error_message,
    )


def generar_aleatorios(cantidad=20, horas=0):
    """Genera actividad normal aleatoria. Si horas > 0, reparte los eventos en ese rango hacia atrás."""
    ahora = timezone.now()
    nombres = list(ACCIONES)
    pesos = [4 if ACCIONES[n]["read_only"] else (3 if n == "ConsoleLogin" else 1) for n in nombres]
    pesos[nombres.index("StopLogging")] = 0.2

    for _ in range(cantidad):
        accion = random.choices(nombres, weights=pesos)[0]
        momento = ahora - timedelta(seconds=random.randint(0, horas * 3600)) if horas else ahora
        ua = None if ACCIONES[accion]["tipo"] == "AwsConsoleSignIn" else random.choice(USER_AGENTS)
        registrar_evento(
            accion,
            random.choice(USUARIOS),
            random.choice(IPS),
            random.choice(REGIONES),
            fallar=random.random() < 0.15,
            user_agent=ua,
            event_time=momento,
        )
    return cantidad


def simular_ataque():
    """Escenario: credenciales robadas de dev.backend usadas desde una IP extranjera."""
    victima = "dev.backend"
    inicio = timezone.now() - timedelta(minutes=5)
    pasos = [("ConsoleLogin", True, None)] * 5 + [
        ("ConsoleLogin", False, None),
        ("ListBuckets", False, None),
        ("AttachUserPolicy", False, {"userName": victima,
                                     "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}),
        ("CreateUser", False, {"userName": "backdoor-user"}),
        ("AuthorizeSecurityGroupIngress", False, None),
        ("StopLogging", False, None),
        ("DeleteBucket", False, {"bucketName": "empresa-backups-001"}),
    ]
    for i, (accion, fallo, params) in enumerate(pasos):
        registrar_evento(
            accion, victima, IP_ATACANTE, "sa-east-1",
            fallar=fallo,
            user_agent=None if accion == "ConsoleLogin" else "aws-cli/2.15.30 Python/3.11.8 Linux/5.15",
            event_time=inicio + timedelta(seconds=i * 20),
            params=params,
        )
    return len(pasos)
