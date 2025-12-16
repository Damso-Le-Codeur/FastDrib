from django.db import models
import secrets
import uuid
# Create your models here.
class SendingGroup(models.Model):
    label = models.TextField(max_length=255)

class SendingUnit(models.Model):
    sending_group = models.ForeignKey(SendingGroup, on_delete=models.CASCADE, related_name='sending_units')
    name = models.TextField(max_length=255)
    email = models.EmailField(max_length=255)
    file = models.FileField(upload_to='sending_files/')
    received = models.BooleanField(default=False)
    sending_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

class Link(models.Model):
    sending_unit = models.ForeignKey(SendingUnit, on_delete=models.CASCADE, related_name='links')
    link = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    access_code = models.CharField(max_length=6, blank=True)
    used = models.BooleanField(default=False)


    def save(self, *args, **kwargs):
        # Générer automatiquement un code à 6 chiffres si absent
        if not self.access_code:
            self.access_code = secrets.randbelow(899999) + 100000 # 100000 à 999999
        super().save(*args, **kwargs)
