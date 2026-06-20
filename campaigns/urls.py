from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup, name='signup'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Contact Upload (standalone)
    path('contacts/', views.contact_upload_list, name='contact_upload_list'),
    path('contacts/upload/', views.contact_upload_csv, name='contact_upload_csv'),
    path('contacts/map-columns/', views.contact_upload_map_columns, name='contact_upload_map_columns'),
    path('contacts/<int:upload_id>/', views.contact_upload_detail, name='contact_upload_detail'),
    path('contacts/<int:upload_id>/delete/', views.contact_upload_delete, name='contact_upload_delete'),

    # Campaign CRUD
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:campaign_id>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:campaign_id>/delete/', views.campaign_delete, name='campaign_delete'),
    path('campaigns/<int:campaign_id>/activate/', views.campaign_activate, name='campaign_activate'),
    path('campaigns/<int:campaign_id>/complete/', views.campaign_complete, name='campaign_complete'),

    # Statistics
    path('campaigns/<int:campaign_id>/statistics/', views.campaign_statistics, name='campaign_statistics'),

    # Task Management
    path('campaigns/<int:campaign_id>/tasks/', views.campaign_tasks, name='campaign_tasks'),
    path('tasks/<int:task_id>/update-status/', views.task_update_status, name='task_update_status'),

    # Public Routes (no auth)
    path('show/', views.show_task_root, name='show_task_root'),
    path('show/<uuid:unique_id>/', views.show_task_detail, name='show_task_detail'),
    path('task/<uuid:unique_id>/done/', views.task_done, name='task_done'),
    path('proof/<uuid:unique_id>/', views.submit_proof, name='submit_proof'),
    path('proof/thank-you/<str:code>/', views.thank_you, name='thank_you'),

    # Proof Search
    path('search-proof/', views.search_proof, name='search_proof'),
    path('proof/<int:task_id>/detail/', views.proof_detail, name='proof_detail'),
]
