from django.urls import path
from . import views
from . import reasoning_views
from . import chat_reasoning

urlpatterns = [
    # Profile URLs
    path('profile/', views.profile_view, name='profile_view'),
    path('save_preferences/', views.save_preferences, name='save_preferences'),

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

    # Code Editor URLs
    path('projects/<int:pk>/editor/', views.code_editor, name='code_editor'),
    path('projects/<int:pk>/file/save/', views.file_save, name='file_save'),
    path('projects/<int:pk>/file/create/', views.file_create, name='file_create'),
    path('projects/<int:pk>/file/delete/', views.file_delete, name='file_delete'),
    path('projects/<int:pk>/file/rename/', views.file_rename, name='file_rename'),

    # Chat API URLs
    path('projects/<int:pk>/chat/', views.chat_with_openai, name='chat_with_openai'),
    path('projects/<int:pk>/chat/history/', views.chat_history, name='chat_history'),
    path('projects/<int:pk>/chat/reasoning/', chat_reasoning.chat_with_reasoning, name='chat_with_reasoning'),

    # File tree API URL
    path('projects/<int:pk>/file-tree/', views.get_file_tree, name='get_file_tree'),

    # Run file API URL
    path('projects/<int:pk>/run-file/', views.run_file, name='run_file'),

    # AI Reasoning URLs
    path('projects/<int:pk>/reasoning/', reasoning_views.reasoning_dashboard, name='reasoning_dashboard'),
    path('projects/<int:pk>/reasoning/sessions/', reasoning_views.get_reasoning_sessions, name='get_reasoning_sessions'),
    path('projects/<int:pk>/reasoning/sessions/<int:session_id>/', reasoning_views.reasoning_session_detail, name='reasoning_session_detail'),
    path('projects/<int:pk>/reasoning/sessions/<int:session_id>/api/', reasoning_views.get_reasoning_session, name='get_reasoning_session'),
    path('projects/<int:pk>/reasoning/start/', reasoning_views.start_reasoning, name='start_reasoning'),
    path('projects/<int:pk>/reasoning/execute/', reasoning_views.execute_full_reasoning, name='execute_full_reasoning'),
    path('projects/<int:pk>/reasoning/sessions/<int:session_id>/step/', reasoning_views.execute_reasoning_step, name='execute_reasoning_step'),
]
