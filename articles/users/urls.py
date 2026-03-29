from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # СПЕЦИФИЧЕСКИЕ URL - должны быть ПЕРЕД <str:username>
    path('register/', views.register, name='register'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('suggestions/', views.suggestions_view, name='suggestions'),
    path('search/', views.search_users, name='search_users'),
    path('feed/', views.feed_view, name='feed'),
    path('messages/', views.chat_inbox, name='chat_inbox'),
    path('messages/<str:username>/', views.chat_thread, name='chat_thread'),
    path('redirect/', views.redirect_after_login, name='redirect_after_login'),

    # URL с username - должны быть ПОСЛЕ специфических
    path('<str:username>/follow/', views.follow_toggle, name='follow_toggle'),
    path('<str:username>/followers/', views.followers_list, name='followers_list'),
    path('<str:username>/following/', views.following_list, name='following_list'),
    path('<str:username>/friend/', views.friend_toggle, name='friend_toggle'),
    path('<str:username>/friends/', views.friends_list, name='friends_list'),
    path('<str:username>/block/', views.block_toggle, name='block_toggle'),

    # САМЫЙ ОБЩИЙ URL - должен быть ПОСЛЕДНИМ
    path('<str:username>/', views.profile_view, name='profile'),
]