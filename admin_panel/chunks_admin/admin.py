from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Chunk, UploadedDocument
from . import views  # добавляем импорт views, чтобы связать с кастомной страницей


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'keywords_preview', 'created_at')
    search_fields = ('text', 'keywords')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def text_preview(self, obj):
        return obj.text[:200]
    text_preview.short_description = "Текст"

    def keywords_preview(self, obj):
        """Отображает первые 5 ключевых слов"""
        words = [w.strip() for w in obj.keywords.split(",") if w.strip()]
        return ", ".join(words[:5])
    keywords_preview.short_description = "Ключевые слова"

    # ✅ Добавляем ссылку на страницу загрузки документов
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'uploaded-documents/',
                self.admin_site.admin_view(views.uploaded_documents_page),
                name='uploaded_documents_page',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Добавляем кнопку-ссылку на страницу загрузки документов"""
        extra_context = extra_context or {}
        extra_context['title'] = 'Чанки'
        extra_context['subtitle'] = format_html(
            '<a href="{}" style="font-size:16px; color:#8F43E3;">Загрузить новый документ</a>',
            reverse("admin:uploaded_documents_page")
        )
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'chunk_count', 'uploaded_at')
    readonly_fields = ('filename', 'chunk_count', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('filename',)

    def has_add_permission(self, request):
        """Запрещаем ручное добавление файлов в админке"""
        return False

    def has_change_permission(self, request, obj=None):
        """Запрещаем ручное редактирование загруженных файлов"""
        return False
