from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Task-related URLs
    path('create-task/', views.create_task, name='create_task'),


    # Project-related URLs
    path('create-project/', views.create_project, name='create_project'),
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    # Feedback-related URLs
    path('submit-feedback/<int:task_id>/', views.submit_feedback, name='submit_feedback'),

    # Invitation-related URLs
    path('view-invitations/', views.view_invitations, name='view_invitations'),
    path('send-invitation/', views.send_invitation, name='send_invitation'),

    # Dashboard URL
    path('', views.dashboard_view, name='dashboard'),

    path('project/<int:project_id>/invite/', views.invite_team_members, name='invite_team_members'),
    path('invitation/<uuid:token>/accept/', views.accept_invitation, name='accept_invitation'),
    path('subscribe/pro/', views.subscribe_pro, name='subscribe_pro'),
    path('upload_task_file/<int:task_id>/', views.upload_task_file, name='upload_task_file'),
    path('download-task-file/<int:task_id>/', views.download_file, name='download_task_file'),
    path('export_project_files/<int:project_id>/', views.export_project_files, name='export_project_files'),



    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
