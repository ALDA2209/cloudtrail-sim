import json
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Evento
from .simulador import (ACCIONES, IPS, REGIONES, USUARIOS,
                        generar_aleatorios, registrar_evento, simular_ataque)

ACCIONES_SENSIBLES = [
    "StopLogging", "AttachUserPolicy", "CreateUser", "DeleteUser",
    "DeleteBucket", "TerminateInstances", "AuthorizeSecurityGroupIngress",
]


def resumen(request):
    if request.method == "POST" and request.POST.get("accion") == "reiniciar":
        Evento.objects.all().delete()
        generar_aleatorios(150, horas=168)
        simular_ataque()
        messages.success(request, "Datos reiniciados: 150 eventos de los últimos 7 días + escenario de ataque.")
        return redirect("resumen")

    qs = Evento.objects.all()
    hoy = timezone.localdate()
    dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]

    por_dia = {
        r["dia"]: r["n"]
        for r in qs.filter(event_time__date__gte=dias[0])
                   .annotate(dia=TruncDate("event_time"))
                   .values("dia").annotate(n=Count("id")).order_by("dia")
    }
    errores_por_dia = {
        r["dia"]: r["n"]
        for r in qs.filter(event_time__date__gte=dias[0]).exclude(error_code="")
                   .annotate(dia=TruncDate("event_time"))
                   .values("dia").annotate(n=Count("id")).order_by("dia")
    }
    servicios = qs.values("event_source").annotate(n=Count("id")).order_by("-n")
    usuarios = qs.values("user_name").annotate(n=Count("id")).order_by("-n")[:6]

    total = qs.count()
    errores = qs.exclude(error_code="").count()

    graficos = {
        "dias": [d.strftime("%d/%m") for d in dias],
        "eventos_dia": [por_dia.get(d, 0) for d in dias],
        "errores_dia": [errores_por_dia.get(d, 0) for d in dias],
        "servicios": [s["event_source"].replace(".amazonaws.com", "") for s in servicios],
        "servicios_n": [s["n"] for s in servicios],
        "resultado": [total - errores, errores],
    }

    return render(request, "trail/resumen.html", {
        "total": total,
        "errores": errores,
        "usuarios_unicos": qs.values("user_name").distinct().count(),
        "ips_unicas": qs.values("source_ip").distinct().count(),
        "logins_fallidos": qs.filter(event_name="ConsoleLogin").exclude(error_code="").count(),
        "top_usuarios": usuarios,
        "sensibles": qs.filter(event_name__in=ACCIONES_SENSIBLES, error_code="")[:8],
        "graficos": graficos,
    })


def panel(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo")

        if tipo == "manual":
            accion = request.POST.get("accion")
            if accion in ACCIONES:
                evento = registrar_evento(
                    accion,
                    request.POST.get("usuario") or "admin",
                    request.POST.get("ip") or IPS[0],
                    request.POST.get("region") or "us-east-1",
                    fallar=request.POST.get("fallar") == "on",
                )
                messages.success(request, f"CloudTrail registró el evento {evento.event_name} de {evento.user_name}.")

        elif tipo == "aleatorio":
            try:
                cantidad = max(1, min(int(request.POST.get("cantidad", 20)), 500))
            except ValueError:
                cantidad = 20
            generar_aleatorios(cantidad)
            messages.success(request, f"Se generaron {cantidad} eventos aleatorios.")

        elif tipo == "ataque":
            total = simular_ataque()
            messages.warning(request, f"Se simuló actividad sospechosa: {total} eventos registrados desde una IP extranjera.")

        return redirect("panel")

    acciones_por_servicio = {}
    for nombre, cfg in ACCIONES.items():
        acciones_por_servicio.setdefault(cfg["servicio"], []).append((nombre, cfg["desc"]))

    return render(request, "trail/panel.html", {
        "acciones_por_servicio": acciones_por_servicio,
        "usuarios": USUARIOS,
        "ips": IPS,
        "regiones": REGIONES,
        "ultimos": Evento.objects.all()[:10],
        "total": Evento.objects.count(),
    })


def filtrar_eventos(params):
    """Aplica los filtros del historial (igual que la consola de CloudTrail)."""
    qs = Evento.objects.all()

    if params.get("usuario"):
        qs = qs.filter(user_name=params["usuario"])
    if params.get("evento"):
        qs = qs.filter(event_name=params["evento"])
    if params.get("servicio"):
        qs = qs.filter(event_source=params["servicio"])
    if params.get("ip"):
        qs = qs.filter(source_ip__icontains=params["ip"].strip())

    if params.get("resultado") == "exito":
        qs = qs.filter(error_code="")
    elif params.get("resultado") == "error":
        qs = qs.exclude(error_code="")

    if params.get("tipo") == "lectura":
        qs = qs.filter(read_only=True)
    elif params.get("tipo") == "escritura":
        qs = qs.filter(read_only=False)

    desde = parse_date(params.get("desde") or "")
    hasta = parse_date(params.get("hasta") or "")
    if desde:
        qs = qs.filter(event_time__date__gte=desde)
    if hasta:
        qs = qs.filter(event_time__date__lte=hasta)

    return qs


def historial(request):
    qs = filtrar_eventos(request.GET)
    pagina = Paginator(qs, 25).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    distintos = Evento.objects.order_by()
    return render(request, "trail/historial.html", {
        "pagina": pagina,
        "total_filtrado": qs.count(),
        "querystring": params.urlencode(),
        "usuarios": sorted(distintos.values_list("user_name", flat=True).distinct()),
        "eventos": sorted(distintos.values_list("event_name", flat=True).distinct()),
        "servicios": sorted(distintos.values_list("event_source", flat=True).distinct()),
    })


def detalle(request, event_id):
    evento = get_object_or_404(Evento, event_id=event_id)
    return render(request, "trail/detalle.html", {
        "e": evento,
        "json_evento": json.dumps(evento.to_cloudtrail(), indent=2, ensure_ascii=False),
    })


def exportar(request):
    qs = filtrar_eventos(request.GET).order_by("event_time", "id")
    data = {"Records": [e.to_cloudtrail() for e in qs]}
    respuesta = JsonResponse(data, json_dumps_params={"indent": 2, "ensure_ascii": False})
    nombre = f"cloudtrail_{timezone.localtime():%Y%m%d_%H%M%S}.json"
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def verificar_cadena():
    """Recorre los eventos en orden y valida la cadena de hashes SHA-256."""
    resultados = []
    anterior = "0" * 64
    for e in Evento.objects.order_by("id"):
        problemas = []
        if e.prev_hash != anterior:
            problemas.append("Enlace roto: falta o se eliminó el evento anterior")
        if e.calcular_hash() != e.hash:
            problemas.append("Contenido modificado después de registrarse")
        resultados.append((e, problemas))
        anterior = e.hash
    return resultados


def integridad(request):
    if request.method == "POST":
        accion = request.POST.get("accion")

        if accion == "manipular":
            objetivo = (Evento.objects.filter(event_name="StopLogging").order_by("-id").first()
                        or Evento.objects.order_by("?").first())
            if objetivo:
                # update() escribe directo en la BD sin recalcular el hash (como un atacante editando el log)
                Evento.objects.filter(pk=objetivo.pk).update(user_name="admin", source_ip="10.0.1.25")
                messages.warning(request, f"Se alteró el evento #{objetivo.pk} ({objetivo.event_name}): "
                                          f"usuario cambiado a 'admin' e IP a una interna para ocultar el rastro.")
            else:
                messages.info(request, "No hay eventos para manipular.")

        elif accion == "eliminar":
            total = Evento.objects.count()
            if total >= 3:
                objetivo = Evento.objects.order_by("id")[total // 2]
                nombre, pk = objetivo.event_name, objetivo.pk
                Evento.objects.filter(pk=pk).delete()
                messages.warning(request, f"Se eliminó el evento #{pk} ({nombre}) directamente de la base de datos.")
            else:
                messages.info(request, "Se necesitan al menos 3 eventos para simular un borrado.")

        return redirect("integridad")

    verificado = request.GET.get("verificar") == "1"
    alterados = []
    total = Evento.objects.count()
    if verificado:
        alterados = [(e, p) for e, p in verificar_cadena() if p]

    return render(request, "trail/integridad.html", {
        "verificado": verificado,
        "alterados": alterados,
        "total": total,
    })
