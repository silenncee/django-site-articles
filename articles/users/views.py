from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from .models import Profile, Message
from ideas.models import Idea
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Count


# ========== РЕГИСТРАЦИЯ ==========

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаем профиль автоматически
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('ideas:idea_list')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

# ========== ПРОФИЛЬ ==========

def profile_view(request, username):
    """
    Просмотр профиля пользователя
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile

    # Проверяем, может ли текущий пользователь видеть этот профиль
    if not profile.can_view_profile(request.user):
        messages.error(request, 'У вас нет доступа к этому профилю')
        return redirect('ideas:idea_list')

    # Получаем идеи пользователя (с проверкой приватности)
    if profile.can_view_ideas(request.user):
        ideas = Idea.objects.filter(author=user).select_related('author').order_by('-created_at')
    else:
        ideas = Idea.objects.none()

    paginator = Paginator(ideas, 10)
    page_number = request.GET.get('page')
    page_ideas = paginator.get_page(page_number)

    # Статистика
    followers_count = profile.total_followers() if profile.can_view_friends(request.user) else 0
    following_count = profile.total_following() if profile.can_view_friends(request.user) else 0
    friends_count = profile.total_friends() if profile.can_view_friends(request.user) else 0
    ideas_count = ideas.count()

    # Базовый контекст
    context = {
        'profile': profile,
        'ideas': page_ideas,
        'followers_count': followers_count,
        'following_count': following_count,
        'friends_count': friends_count,
        'ideas_count': ideas_count,
        'social_links': profile.get_social_links(),
        'can_view_friends': profile.can_view_friends(request.user),
    }

    # Если пользователь авторизован и это не его профиль
    if request.user.is_authenticated and request.user != user:
        viewer_profile = request.user.profile
        context['relationship'] = viewer_profile.get_relationship_status(profile)
        context['is_friend'] = viewer_profile.is_friend(profile)
        context['is_following'] = viewer_profile.is_following(profile)
        context['is_follower'] = viewer_profile.is_follower(profile)  # Добавлено!
        context['is_blocked'] = viewer_profile.is_blocked(profile)
        context['is_blocked_by'] = viewer_profile.is_blocked_by(profile)
        context['mutual_friends'] = viewer_profile.get_mutual_friends(profile)
        context['can_send_message'] = profile.can_send_message(request.user)
        context['can_be_friends'] = context['is_following'] and context['is_follower'] and not context[
            'is_friend']  # Добавлено!

    return render(request, 'users/profile.html', context)

@login_required
def block_toggle(request, username):
    """
    Заблокировать/разблокировать пользователя
    """
    target_user = get_object_or_404(User, username=username)
    target_profile = target_user.profile
    user_profile = request.user.profile

    if request.user == target_user:
        messages.error(request, 'Нельзя заблокировать самого себя')
        return redirect('users:profile', username=username)

    if request.method == 'POST':
        if user_profile.is_blocked(target_profile):
            user_profile.unblock_user(target_profile)
            messages.success(request, f'Пользователь {target_user.username} разблокирован')
        else:
            user_profile.block_user(target_profile)
            messages.success(request, f'Пользователь {target_user.username} заблокирован')

    return redirect('users:profile', username=username)


@login_required
def profile_edit(request):
    """
    Редактирование своего профиля
    """
    profile = request.user.profile
    user = request.user

    if request.method == 'POST':
        # Получаем данные из формы
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        bio = request.POST.get('bio', '')
        avatar = request.FILES.get('avatar')

        # Социальные сети
        profile.website = request.POST.get('website', '')
        profile.github = request.POST.get('github', '')
        profile.telegram = request.POST.get('telegram', '')
        profile.instagram = request.POST.get('instagram', '')
        profile.twitter = request.POST.get('twitter', '')
        profile.linkedin = request.POST.get('linkedin', '')

        # Приватность
        profile.privacy_profile = request.POST.get('privacy_profile', 'public')
        profile.privacy_ideas = request.POST.get('privacy_ideas', 'public')
        profile.privacy_friends = request.POST.get('privacy_friends', 'public')

        # Проверяем уникальность username (если изменился)
        if username != user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Пользователь с таким именем уже существует!')
                return render(request, 'users/profile_edit.html', {'profile': profile})

        # Проверяем уникальность email (если изменился)
        if email != user.email:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Пользователь с таким email уже существует!')
                return render(request, 'users/profile_edit.html', {'profile': profile})

        # Сохраняем изменения в User
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        try:
            user.save()
        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении. Возможно, такое имя пользователя или email уже заняты.')
            return render(request, 'users/profile_edit.html', {'profile': profile})

        # Сохраняем bio и avatar в профиль
        profile.bio = bio
        if avatar:
            # Удаляем старый аватар, если есть
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = avatar
        profile.save()

        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('users:profile', username=user.username)

    return render(request, 'users/profile_edit.html', {'profile': profile})


# ========== ПОДПИСКИ ==========

@login_required
def follow_toggle(request, username):
    """
    Подписаться/отписаться
    """
    target_user = get_object_or_404(User, username=username)
    target_profile = target_user.profile
    user_profile = request.user.profile

    if request.user == target_user:
        messages.error(request, 'Нельзя подписаться на самого себя')
        return redirect('users:profile', username=username)

    if request.method == 'POST':
        if user_profile.is_following(target_profile):
            user_profile.unfollow(target_profile)
            messages.success(request, f'Вы отписались от {target_user.username}')
        else:
            user_profile.follow(target_profile)
            messages.success(request, f'Вы подписались на {target_user.username}')

    return redirect('users:profile', username=username)


@login_required
def followers_list(request, username):
    """
    Список подписчиков
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile

    # Получаем подписчиков через related_name 'followers'
    followers = profile.followers.select_related('user')

    # Добавляем информацию о взаимоотношениях для текущего пользователя
    if request.user.is_authenticated:
        current_profile = request.user.profile
        for follower in followers:
            follower.relationship = current_profile.get_relationship_status(follower)

    paginator = Paginator(followers, 20)
    page_number = request.GET.get('page')
    page_followers = paginator.get_page(page_number)

    return render(request, 'users/followers_list.html', {
        'profile': profile,
        'users': page_followers,
        'title': f'Подписчики {user.username}'
    })


@login_required
def following_list(request, username):
    """
    Список подписок
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile

    # Получаем подписки через поле 'follows'
    following = profile.follows.select_related('user')

    if request.user.is_authenticated:
        current_profile = request.user.profile
        for followed in following:
            followed.relationship = current_profile.get_relationship_status(followed)

    paginator = Paginator(following, 20)
    page_number = request.GET.get('page')
    page_following = paginator.get_page(page_number)

    return render(request, 'users/following_list.html', {
        'profile': profile,
        'users': page_following,
        'title': f'Подписки {user.username}'
    })


# ========== ДРУЗЬЯ ==========
@login_required
def friend_toggle(request, username):
    """
    Добавить/удалить друга (только если есть взаимная подписка)
    """
    target_user = get_object_or_404(User, username=username)
    target_profile = target_user.profile
    user_profile = request.user.profile

    if request.user == target_user:
        messages.error(request, 'Нельзя добавить себя в друзья')
        return redirect('users:profile', username=username)

    # Проверяем, есть ли взаимная подписка
    if not (user_profile.is_following(target_profile) and target_profile.is_following(user_profile)):
        messages.error(request, 'Чтобы добавить в друзья, нужно быть взаимно подписанными')
        return redirect('users:profile', username=username)

    if request.method == 'POST':
        if user_profile.is_friend(target_profile):
            user_profile.remove_friend(target_profile)
            messages.success(request, f'{target_user.username} удален из друзей')
        else:
            # Добавляем в друзья (они уже подписаны друг на друга)
            # В модели add_friend может просто возвращать True, если уже есть взаимная подписка
            user_profile.add_friend(target_profile)
            messages.success(request, f'{target_user.username} добавлен в друзья')

    return redirect('users:profile', username=username)

def friends_list(request, username):
    """
    Список друзей (взаимные подписки)
    """
    user = get_object_or_404(User, username=username)
    profile = user.profile

    # Используем метод get_friends() вместо поля friends
    friends = profile.get_friends().select_related('user')

    if request.user.is_authenticated:
        current_profile = request.user.profile
        for friend in friends:
            friend.relationship = current_profile.get_relationship_status(friend)

    paginator = Paginator(friends, 20)
    page_number = request.GET.get('page')
    page_friends = paginator.get_page(page_number)

    return render(request, 'users/friends_list.html', {
        'profile': profile,
        'users': page_friends,
        'title': f'Друзья {user.username}'
    })
# ========== РЕКОМЕНДАЦИИ И ПОИСК ==========

@login_required
def suggestions_view(request):
    """
    Рекомендации для подписки
    """
    profile = request.user.profile
    suggestions = profile.get_suggestions(limit=20).select_related('user')

    return render(request, 'users/suggestions.html', {
        'suggestions': suggestions,
        'title': 'Рекомендации'
    })


@login_required
def search_users(request):
    """
    Поиск пользователей
    """
    raw = (request.GET.get('q', '') or '').strip()
    query = raw[1:].strip() if raw.startswith('@') else raw

    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id).select_related('profile')[:30]

        # Добавляем информацию о взаимоотношениях
        current_profile = request.user.profile
        for user in users:
            user.relationship = current_profile.get_relationship_status(user.profile)
    else:
        users = []

    return render(request, 'users/search_results.html', {
        'users': users,
        'query': query,
        'raw_query': raw,
        'title': 'Поиск пользователей'
    })


@login_required
def feed_view(request):
    """
    Лента активности (идеи от друзей и подписок)
    """
    profile = request.user.profile
    filter_type = request.GET.get('type', 'all')

    # Получаем идеи от друзей и подписок
    ideas = profile.get_activity_feed(limit=50)

    # Здесь можно добавить другие типы активностей
    # Например, комментарии, лайки, новые друзья и т.д.

    # Для простоты пока просто передаем идеи
    paginator = Paginator(ideas, 10)
    page_number = request.GET.get('page')
    page_ideas = paginator.get_page(page_number)

    # Преобразуем идеи в формат активностей
    activities = []
    for idea in page_ideas:
        activities.append({
            'type': 'idea',
            'user': idea.author,
            'idea': idea,
            'created_at': idea.created_at
        })

    # Рекомендации для боковой панели
    suggestions = profile.get_suggestions(limit=5)

    # Статистика лайков (пример)
    total_likes_received = Idea.objects.filter(
        author=request.user
    ).aggregate(total=Count('likes'))['total']

    return render(request, 'users/feed.html', {
        'activities': activities,
        'suggestions': suggestions,
        'total_likes_received': total_likes_received,
        'type': filter_type,
    })

@login_required
def redirect_after_login(request):
    """
    Перенаправляет пользователя на его профиль после входа
    """
    return redirect('users:profile', username=request.user.username)


# ========== СООБЩЕНИЯ (ЧАТ) ==========

def _conversation_partners(user):
    """Пользователи, с которыми уже есть переписка (для списка диалогов)."""
    partner_ids = set(
        Message.objects.filter(sender=user).values_list('recipient_id', flat=True)
    )
    partner_ids.update(
        Message.objects.filter(recipient=user).values_list('sender_id', flat=True)
    )
    partner_ids.discard(user.id)
    return User.objects.filter(id__in=partner_ids).select_related('profile')


@login_required
def chat_inbox(request):
    """
    Список диалогов (собеседники из переписки + подписчики/подписки для быстрого старта).
    """
    user = request.user
    partners = _conversation_partners(user)
    last_by_partner = {}
    for msg in Message.objects.filter(
        Q(sender=user) | Q(recipient=user)
    ).select_related('sender', 'recipient').order_by('-created_at'):
        other = msg.recipient if msg.sender_id == user.id else msg.sender
        if other.id not in last_by_partner:
            last_by_partner[other.id] = msg

    conv_rows = []
    for other in partners:
        last = last_by_partner.get(other.id)
        unread = Message.objects.filter(
            sender=other, recipient=user, read_at__isnull=True
        ).count()
        conv_rows.append({
            'user': other,
            'last_message': last,
            'unread': unread,
        })
    conv_rows.sort(
        key=lambda r: r['last_message'].created_at if r['last_message'] else r['user'].date_joined,
        reverse=True,
    )

    profile = user.profile
    follower_profiles = list(
        profile.followers.select_related('user').exclude(user_id=user.id)[:30]
    )
    following_profiles = list(
        profile.follows.select_related('user').exclude(user_id=user.id)[:30]
    )

    return render(request, 'users/chat_inbox.html', {
        'conversations': conv_rows,
        'followers': [{'profile': p, 'can_chat': p.can_send_message(user)} for p in follower_profiles],
        'following': [{'profile': p, 'can_chat': p.can_send_message(user)} for p in following_profiles],
        'title': 'Сообщения',
    })


@login_required
def chat_thread(request, username):
    """
    Переписка с пользователем: история + отправка нового сообщения.
    """
    peer = get_object_or_404(User, username=username)
    if peer.id == request.user.id:
        messages.error(request, 'Нельзя открыть чат с собой')
        return redirect('users:chat_inbox')

    peer_profile = peer.profile
    if not peer_profile.can_send_message(request.user):
        messages.error(request, 'Вы не можете писать этому пользователю')
        return redirect('users:profile', username=username)

    qs = Message.objects.filter(
        Q(sender=request.user, recipient=peer) |
        Q(sender=peer, recipient=request.user)
    ).select_related('sender', 'recipient').order_by('created_at')

    if request.method == 'POST':
        body = (request.POST.get('body') or '').strip()
        if not body:
            messages.error(request, 'Введите текст сообщения')
        else:
            Message.objects.create(
                sender=request.user,
                recipient=peer,
                body=body,
            )
            messages.success(request, 'Сообщение отправлено')
        return redirect('users:chat_thread', username=username)

    Message.objects.filter(
        sender=peer, recipient=request.user, read_at__isnull=True
    ).update(read_at=timezone.now())

    return render(request, 'users/chat_thread.html', {
        'peer': peer,
        'peer_profile': peer_profile,
        'message_list': qs,
        'can_send': peer_profile.can_send_message(request.user),
        'title': f'Чат с {peer.username}',
    })