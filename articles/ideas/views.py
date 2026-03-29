from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse

from .forms import IdeaForm, CommentForm
from .models import Idea, Comment

User = get_user_model()

# ========== ГЛАВНАЯ И СПИСОК ИДЕЙ ==========

def idea_list(request):
    """
    Главная страница со списком всех идей
    """
    # Аннотируем каждую идею количеством лайков
    ideas = Idea.objects.annotate(
        likes_count=Count('likes')
    ).select_related('author').prefetch_related('comments')

    # Поиск: обычный текст по идеям; с @ — акцент на людей и идеи автора
    query = request.GET.get('q')
    query = query.strip() if query else None
    user_search_term = None
    user_hits = []
    if query:
        if query.startswith('@'):
            user_search_term = query[1:].strip()
            if user_search_term:
                uh = User.objects.filter(
                    Q(username__icontains=user_search_term) |
                    Q(first_name__icontains=user_search_term) |
                    Q(last_name__icontains=user_search_term)
                ).select_related('profile')
                if request.user.is_authenticated:
                    uh = uh.exclude(id=request.user.id)
                user_hits = list(uh[:20])
                if request.user.is_authenticated:
                    current_profile = request.user.profile
                    for u in user_hits:
                        u.relationship = current_profile.get_relationship_status(u.profile)
                ideas = ideas.filter(author__username__icontains=user_search_term)
            else:
                ideas = ideas.none()
        else:
            ideas = ideas.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(author__username__icontains=query) |
                Q(author__profile__website__icontains=query)
            )

    # Сортировка
    sort = request.GET.get('sort', '-created_at')
    if sort == 'total_likes' or sort == '-total_likes':
        # Сортируем по аннотированному полю likes_count
        if sort.startswith('-'):
            ideas = ideas.order_by('-likes_count')
        else:
            ideas = ideas.order_by('likes_count')
    else:
        # Для остальных полей сортируем как обычно
        if sort in ['created_at', '-created_at', 'title', '-title']:
            ideas = ideas.order_by(sort)

    # Пагинация
    paginator = Paginator(ideas, 9)
    page_number = request.GET.get('page')
    page_ideas = paginator.get_page(page_number)

    return render(request, 'ideas/idea_list.html', {
        'ideas': page_ideas,
        'query': query,
        'sort': sort,
        'user_hits': user_hits,
        'user_search_term': user_search_term,
    })


def idea_detail(request, idea_id):
    """
    Детальная страница идеи с комментариями
    """
    idea = get_object_or_404(
        Idea.objects.select_related('author').prefetch_related(
            'comments__author', 'likes'
        ),
        id=idea_id
    )

    # Получаем комментарии (только корневые, ответы будут в шаблоне)
    comments = idea.comments.filter(parent__isnull=True).select_related('author').prefetch_related('replies__author')

    # Проверяем, лайкнул ли текущий пользователь эту идею
    if request.user.is_authenticated:
        user_liked = idea.likes.filter(id=request.user.id).exists()
        # Проверяем подписку на автора
        is_following = request.user.profile.is_following(idea.author.profile)
    else:
        user_liked = False
        is_following = False

    return render(request, 'ideas/idea_detail.html', {
        'idea': idea,
        'comments': comments,
        'user_liked': user_liked,
        'is_following': is_following,
    })

# ========== CRUD ДЛЯ ИДЕЙ ==========

@login_required
def idea_create(request):
    """
    Создание новой идеи
    """
    if request.method == 'POST':
        form = IdeaForm(request.POST, request.FILES)
        if form.is_valid():
            idea = form.save(commit=False)
            idea.author = request.user
            idea.save()
            messages.success(request, 'Идея успешно создана!')
            return redirect('ideas:idea_detail', idea_id=idea.id)  # <- ИСПРАВЛЕНО: добавил ideas:
    else:
        form = IdeaForm()

    return render(request, 'ideas/idea_form.html', {
        'form': form,
        'title': 'Создать идею',
        'button_text': 'Опубликовать'
    })


@login_required
def idea_edit(request, idea_id):
    """
    Редактирование идеи
    """
    idea = get_object_or_404(Idea, id=idea_id)

    # Проверяем, что автор - текущий пользователь
    if idea.author != request.user:
        messages.error(request, 'Вы не можете редактировать чужую идею')
        return redirect('ideas:idea_detail', idea_id=idea.id)  # ИСПРАВЛЕНО

    if request.method == 'POST':
        form = IdeaForm(request.POST, request.FILES, instance=idea)
        if form.is_valid():
            form.save()
            messages.success(request, 'Идея успешно обновлена!')
            return redirect('ideas:idea_detail', idea_id=idea.id)  # ИСПРАВЛЕНО
    else:
        form = IdeaForm(instance=idea)

    return render(request, 'ideas/idea_form.html', {
        'form': form,
        'title': 'Редактировать идею',
        'button_text': 'Сохранить',
        'idea': idea
    })


@login_required
def idea_delete(request, idea_id):
    """
    Удаление идеи
    """
    idea = get_object_or_404(Idea, id=idea_id)

    # Проверяем, что автор - текущий пользователь
    if idea.author != request.user:
        messages.error(request, 'Вы не можете удалить чужую идею')
        return redirect('ideas:idea_detail', idea_id=idea.id)  # ИСПРАВЛЕНО

    if request.method == 'POST':
        idea.delete()
        messages.success(request, 'Идея удалена')
        return redirect('ideas:idea_list')  # ИСПРАВЛЕНО (было 'idea_list')

    return render(request, 'ideas/idea_confirm_delete.html', {
        'idea': idea
    })


# ========== ЛАЙКИ ==========

@login_required
def like_toggle(request, idea_id):
    """
    Поставить/убрать лайк
    """
    idea = get_object_or_404(Idea, id=idea_id)

    if request.method == 'POST':
        if idea.likes.filter(id=request.user.id).exists():
            idea.likes.remove(request.user)
            liked = False
            messages.success(request, 'Лайк убран')
        else:
            idea.likes.add(request.user)
            liked = True
            messages.success(request, 'Лайк поставлен!')

        # Если это AJAX-запрос, возвращаем JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': liked,
                'total_likes': idea.likes.count()
            })

        # Иначе редирект обратно
        return redirect(request.META.get('HTTP_REFERER', 'ideas:idea_detail'))

    return redirect('ideas:idea_detail', idea_id=idea.id)

# ========== КОММЕНТАРИИ ==========

@login_required

def add_comment(request, idea_id):
    """
    Добавить комментарий к идее
    """
    idea = get_object_or_404(Idea, id=idea_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.idea = idea
            comment.author = request.user

            # Проверяем, является ли комментарий ответом
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id, idea=idea)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    messages.error(request, 'Ошибка: комментарий-родитель не найден')
                    return redirect('ideas:idea_detail', idea_id=idea.id)  # ИСПРАВЛЕНО

            comment.save()
            messages.success(request, 'Комментарий добавлен!')

    return redirect('ideas:idea_detail', idea_id=idea.id)  # ИСПРАВЛЕНО


@login_required
def delete_comment(request, comment_id):
    """
    Удалить комментарий
    """
    comment = get_object_or_404(Comment, id=comment_id)
    idea_id = comment.idea.id

    # Проверяем права: автор комментария или автор идеи
    if request.user == comment.author or request.user == comment.idea.author:
        comment.delete()
        messages.success(request, 'Комментарий удален')
    else:
        messages.error(request, 'Нет прав на удаление этого комментария')

    return redirect('ideas:idea_detail', idea_id=idea_id)  # ИСПРАВЛЕНО