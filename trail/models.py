import hashlib
import json
import uuid
from datetime import timezone as dt_timezone

from django.db import models
from django.utils import timezone


class Evento(models.Model):
    TIPO_EVENTO = [
        ("AwsApiCall", "AwsApiCall"),
        ("AwsConsoleSignIn", "AwsConsoleSignIn"),
    ]

    event_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_time = models.DateTimeField(default=timezone.now)
    event_name = models.CharField(max_length=100)
    event_source = models.CharField(max_length=100)
    event_type = models.CharField(max_length=30, choices=TIPO_EVENTO, default="AwsApiCall")
    read_only = models.BooleanField(default=False)
    user_name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=30, default="IAMUser")
    source_ip = models.GenericIPAddressField()
    aws_region = models.CharField(max_length=30, default="us-east-1")
    user_agent = models.CharField(max_length=200, default="console.amazonaws.com")
    request_parameters = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.CharField(max_length=255, blank=True)

    prev_hash = models.CharField(max_length=64, editable=False)
    hash = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ["-event_time", "-id"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return f"{self.event_name} - {self.user_name} - {self.event_time:%Y-%m-%d %H:%M:%S}"

    @property
    def exitoso(self):
        return not self.error_code

    def to_cloudtrail(self):
        """Devuelve el evento con el mismo formato JSON que CloudTrail real."""
        data = {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": self.user_type,
                "userName": self.user_name,
                "accountId": "123456789012",
            },
            "eventTime": self.event_time.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "eventSource": self.event_source,
            "eventName": self.event_name,
            "awsRegion": self.aws_region,
            "sourceIPAddress": self.source_ip,
            "userAgent": self.user_agent,
            "requestParameters": self.request_parameters,
            "eventID": str(self.event_id),
            "readOnly": self.read_only,
            "eventType": self.event_type,
            "recipientAccountId": "123456789012",
        }
        if self.error_code:
            data["errorCode"] = self.error_code
            data["errorMessage"] = self.error_message
        return data

    def calcular_hash(self):
        contenido = json.dumps(self.to_cloudtrail(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256((contenido + self.prev_hash).encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if not self.pk:
            ultimo = Evento.objects.order_by("-id").first()
            self.prev_hash = ultimo.hash if ultimo else "0" * 64
            self.hash = self.calcular_hash()
        super().save(*args, **kwargs)
