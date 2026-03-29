from django.urls import path
from . import views

app_name = 'ideas'

urlpatterns = [
    # Главная и детали
    path('', views.idea_list, name='idea_list'),
    path('idea/<int:idea_id>/', views.idea_detail, name='idea_detail'),

    # CRUD для идей
    path('idea/create/', views.idea_create, name='idea_create'),
    path('idea/<int:idea_id>/edit/', views.idea_edit, name='idea_edit'),
    path('idea/<int:idea_id>/delete/', views.idea_delete, name='idea_delete'),

    # Лайки
    path('idea/<int:idea_id>/like/', views.like_toggle, name='like_toggle'),

    # Комментарии
    path('idea/<int:idea_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
]