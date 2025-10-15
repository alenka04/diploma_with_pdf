from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import requests
import json

class Chunk(models.Model):
    text = models.TextField("Текст чанка")
    keywords = models.CharField("Ключевые слова", max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:60] + "..." if len(self.text) > 60 else self.text

    class Meta:
        verbose_name = "Чанк"
        verbose_name_plural = "Чанки"
        ordering = ['-created_at']


# Ссылка на FastAPI
FASTAPI_URL = "http://localhost:8000/admin/sync_chunk"

@receiver(post_save, sender=Chunk)
def chunk_saved(sender, instance, created, **kwargs):
    action = "add" if created else "update"
    
    try:
        response = requests.post(
            FASTAPI_URL,
            data=json.dumps({
                "action": action,
                "id": instance.id,
                "text": instance.text,
                "keywords": instance.keywords.split(",") if instance.keywords else []
            }),
            headers={"Content-Type": "application/json"}
        )
        print(f"Синхронизация {action}: статус {response.status_code}")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

@receiver(post_delete, sender=Chunk)
def chunk_deleted(sender, instance, **kwargs):
    try:
        response = requests.post(
            FASTAPI_URL,
            data=json.dumps({
                "action": "delete",
                "id": instance.id
            }),
            headers={"Content-Type": "application/json"}
        )
        print(f"Удаление синхронизировано: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при удалении: {e}")


class UploadedDocument(models.Model):
    file = models.FileField("Файл", upload_to="uploaded_documents/")
    filename = models.CharField("Имя файла", max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    chunk_count = models.PositiveIntegerField("Количество чанков", default=0)

    def __str__(self):
        return self.filename

    class Meta:
        verbose_name = "Загруженный документ"
        verbose_name_plural = "Загруженные документы"
        ordering = ['-uploaded_at']