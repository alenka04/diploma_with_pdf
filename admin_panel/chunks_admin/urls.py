from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.uploaded_documents_page, name='uploaded_documents_page'),
]