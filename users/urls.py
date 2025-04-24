from django.urls import path
from . import views

urlpatterns = [
    # Profile URLs
    path('profile/', views.profile_view, name='profile_view'),

    # Project URLs
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/update/', views.project_update, name='project_update'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),

    # Container Management URLs
    path('projects/<int:pk>/container/create/', views.container_create, name='container_create'),
    path('projects/<int:pk>/container/start/', views.container_start, name='container_start'),
    path('projects/<int:pk>/container/stop/', views.container_stop, name='container_stop'),
    path('projects/<int:pk>/container/remove/', views.container_remove, name='container_remove'),
    path('projects/<int:pk>/container/status/', views.container_status, name='container_status'),
]
