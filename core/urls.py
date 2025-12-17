from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

from django.urls import path
from . import views

urlpatterns = [
        path('', views.home, name='home'),
  
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('download/<uuid:token>/', views.download_file_view, name='download_file'),
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('admin/create/', views.create_group, name='create_group'),
    path('admin/group/<int:group_id>/', views.group_detail, name='group_detail'),
    path('admin/group/<int:group_id>/send/', views.send_emails, name='send_emails'),
    path('admin/unit/<int:unit_id>/resend/', views.resend_link, name='resend_link'),
    path('admin/group/<int:group_id>/export/', views.export_results, name='export_results'),
    path('admin/create_user/', views.create_user_view, name='create_user_view')

]
