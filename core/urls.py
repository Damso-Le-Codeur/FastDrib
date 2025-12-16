from django.urls import path
from . import views

urlpatterns = [
    path('download/<uuid:token>/', views.download_file_view, name='secure_download'),
]