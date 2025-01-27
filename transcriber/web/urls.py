from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('job/<int:job_id>/', views.job_status, name='job_status'),
    path('job/<int:job_id>/status/', views.check_status, name='check_status'),
]
