from django.shortcuts import redirect

def redirect_after_login(request):
    """Перенаправляет пользователя на его профиль после входа"""
    if request.user.is_authenticated:
        return redirect('users:profile', username=request.user.username)
    return redirect('ideas:idea_list')