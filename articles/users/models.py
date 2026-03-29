from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# В классе Profile можно добавить метод clean, но это для админки

# Статусы онлайн
ONLINE_STATUS = [
    ('online', 'Онлайн'),
    ('offline', 'Офлайн'),
    ('away', 'Отошел'),
]

# Настройки приватности
PRIVACY_CHOICES = [
    ('public', 'Публичный - видят все'),
    ('friends', 'Только друзья'),
    ('private', 'Приватный - только я'),
]


class Profile(models.Model):
    """
    Профиль пользователя
    """
    # Основная информация
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    bio = models.TextField(
        'О себе',
        max_length=500,
        blank=True
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        null=True
    )

    # Социальные сети
    website = models.URLField(
        'Веб-сайт',
        max_length=200,
        blank=True,
        help_text='Ваш личный сайт или блог'
    )
    github = models.URLField(
        'GitHub',
        max_length=200,
        blank=True,
        help_text='Ссылка на GitHub профиль'
    )
    telegram = models.CharField(
        'Telegram',
        max_length=100,
        blank=True,
        help_text='Ваш Telegram username (без @)'
    )
    instagram = models.CharField(
        'Instagram',
        max_length=100,
        blank=True,
        help_text='Ваш Instagram username'
    )
    twitter = models.CharField(
        'Twitter',
        max_length=100,
        blank=True,
        help_text='Ваш Twitter username'
    )
    linkedin = models.URLField(
        'LinkedIn',
        max_length=200,
        blank=True,
        help_text='Ссылка на LinkedIn профиль'
    )

    # Подписки
    follows = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True,
        verbose_name='Подписки'
    )

    # Заблокированные пользователи
    blocked_users = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocked_by',
        blank=True,
        verbose_name='Заблокированные пользователи'
    )

    # Настройки приватности
    privacy_profile = models.CharField(
        'Кто видит профиль',
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
    privacy_ideas = models.CharField(
        'Кто видит идеи',
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
    privacy_friends = models.CharField(
        'Кто видит список друзей',
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )

    # Статус онлайн
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=ONLINE_STATUS,
        default='offline'
    )
    last_seen = models.DateTimeField(
        'Последний визит',
        auto_now=True
    )

    # Кэшированные счетчики (для оптимизации)
    followers_count = models.PositiveIntegerField(
        'Количество подписчиков',
        default=0
    )
    following_count = models.PositiveIntegerField(
        'Количество подписок',
        default=0
    )
    friends_count = models.PositiveIntegerField(
        'Количество друзей',
        default=0
    )
    ideas_count = models.PositiveIntegerField(
        'Количество идей',
        default=0
    )

    # Мета-информация
    created_at = models.DateTimeField(
        'Дата регистрации',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-created_at']

    def __str__(self):
        return f'Профиль {self.user.username}'

    # ========== МЕТОДЫ ДЛЯ ПОДПИСОК ==========

    def follow(self, profile):
        """Подписаться на пользователя"""
        if profile != self and not self.is_following(profile) and not self.is_blocked(profile):
            self.follows.add(profile)
            self.update_counts()
            profile.update_counts()
            return True
        return False

    def unfollow(self, profile):
        """Отписаться от пользователя"""
        if self.is_following(profile):
            self.follows.remove(profile)
            self.update_counts()
            profile.update_counts()
            return True
        return False

    def is_following(self, profile):
        """Проверяет, подписан ли текущий пользователь на указанный профиль"""
        return self.follows.filter(id=profile.id).exists()

    def is_follower(self, profile):
        """Проверяет, подписан ли указанный профиль на текущего пользователя"""
        return self.followers.filter(id=profile.id).exists()

    def total_following(self):
        """Количество подписок"""
        return self.follows.count()

    def total_followers(self):
        """Количество подписчиков"""
        return self.followers.count()

    # ========== МЕТОДЫ ДЛЯ ДРУЗЕЙ (ВЗАИМНЫЕ ПОДПИСКИ) ==========

    def get_friends(self):
        """Возвращает queryset друзей (взаимные подписки)"""
        # Друзья - это те, на кого я подписан И кто подписан на меня
        return self.follows.filter(followers=self)

    def add_friend(self, profile):
        """Добавить в друзья (подписаться взаимно)"""
        if profile != self and not self.is_friend(profile) and not self.is_blocked(profile):
            # Если уже есть взаимная подписка, просто отмечаем как друзей
            if self.is_following(profile) and profile.is_following(self):
                # Здесь можно создать запись о дружбе, если нужно
                # Но так как друзья = взаимная подписка, можно просто вернуть True
                return True
            return False
        return False

    def remove_friend(self, profile):
        """Удалить из друзей (отписаться друг от друга)"""
        if self.is_friend(profile):
            # Отписываемся друг от друга
            self.unfollow(profile)
            profile.unfollow(self)
            return True
        return False

    def is_friend(self, profile):
        """Проверяет, является ли пользователь другом (взаимная подписка)"""
        return self.is_following(profile) and profile.is_following(self)

    def total_friends(self):
        """Количество друзей (взаимных подписок)"""
        return self.get_friends().count()

    def get_mutual_friends(self, profile):
        """Возвращает общих друзей с указанным профилем"""
        # Общие друзья - это пересечение списков друзей
        my_friends_ids = set(self.get_friends().values_list('id', flat=True))
        their_friends_ids = set(profile.get_friends().values_list('id', flat=True))
        mutual_ids = my_friends_ids.intersection(their_friends_ids)
        return Profile.objects.filter(id__in=mutual_ids)

    # ========== МЕТОДЫ ДЛЯ БЛОКИРОВОК ==========

    def block_user(self, profile):
        """Заблокировать пользователя"""
        if profile != self and not self.is_blocked(profile):
            # При блокировке удаляем из друзей и подписок
            if self.is_friend(profile):
                self.remove_friend(profile)
            if self.is_following(profile):
                self.unfollow(profile)
            if profile.is_following(self):
                profile.unfollow(self)

            self.blocked_users.add(profile)
            self.update_counts()
            profile.update_counts()
            return True
        return False

    def unblock_user(self, profile):
        """Разблокировать пользователя"""
        if self.is_blocked(profile):
            self.blocked_users.remove(profile)
            self.update_counts()
            profile.update_counts()
            return True
        return False

    def is_blocked(self, profile):
        """Проверяет, заблокирован ли пользователь"""
        return self.blocked_users.filter(id=profile.id).exists()

    def is_blocked_by(self, profile):
        """Проверяет, заблокирован ли текущий пользователь указанным"""
        return profile.blocked_users.filter(id=self.id).exists()

    # ========== МЕТОДЫ ДЛЯ ПРОВЕРКИ ПРАВ ДОСТУПА ==========

    def can_view_profile(self, user):
        """Проверяет, может ли пользователь видеть этот профиль"""
        if not user.is_authenticated:
            return self.privacy_profile == 'public'

        viewer = user.profile

        # Если это свой профиль - всегда видно
        if viewer == self:
            return True

        # Проверяем блокировки - но не скрываем профиль полностью
        # Просто покажем специальное сообщение в шаблоне
        if self.is_blocked(viewer) or self.is_blocked_by(viewer):
            return True  # Разрешаем просмотр, но с ограничениями

        # Проверка приватности
        if self.privacy_profile == 'public':
            return True
        elif self.privacy_profile == 'friends':
            return self.is_friend(viewer)
        elif self.privacy_profile == 'private':
            return False
        return False

    def can_view_ideas(self, user):
        """Проверяет, может ли пользователь видеть идеи пользователя"""
        if not user.is_authenticated:
            return self.privacy_ideas == 'public'

        viewer = user.profile

        # Проверяем блокировки
        if self.is_blocked(viewer) or self.is_blocked_by(viewer):
            return False

        if self.privacy_ideas == 'public':
            return True
        elif self.privacy_ideas == 'friends':
            return self.is_friend(viewer) or viewer == self
        elif self.privacy_ideas == 'private':
            return viewer == self
        return False

    def can_view_friends(self, user):
        """Проверяет, может ли пользователь видеть список друзей"""
        if not user.is_authenticated:
            return self.privacy_friends == 'public'

        viewer = user.profile

        # Проверяем блокировки
        if self.is_blocked(viewer) or self.is_blocked_by(viewer):
            return False

        if self.privacy_friends == 'public':
            return True
        elif self.privacy_friends == 'friends':
            return self.is_friend(viewer) or viewer == self
        elif self.privacy_friends == 'private':
            return viewer == self
        return False

    def can_send_message(self, user):
        """Проверяет, может ли пользователь отправить сообщение"""
        if not user.is_authenticated:
            return False

        sender = user.profile

        # Проверяем блокировки
        if self.is_blocked(sender) or self.is_blocked_by(sender):
            return False

        # Друзья, подписчики, взаимная подписка (вы подписаны на этого пользователя)
        if self.is_friend(sender) or self.is_follower(sender) or self.is_following(sender):
            return True

        # Уже есть переписка — можно отвечать собеседнику
        return Message.objects.filter(
            models.Q(sender=user, recipient=self.user) |
            models.Q(sender=self.user, recipient=user)
        ).exists()

    # ========== МЕТОДЫ ДЛЯ СТАТУСА ==========

    def update_status(self, status):
        """Обновляет статус онлайн"""
        if status in dict(ONLINE_STATUS):
            self.status = status
            self.save(update_fields=['status', 'last_seen'])

    def go_online(self):
        """Устанавливает статус онлайн"""
        self.update_status('online')

    def go_offline(self):
        """Устанавливает статус офлайн"""
        self.update_status('offline')

    def is_online(self):
        """Проверяет, онлайн ли пользователь"""
        return self.status == 'online'

    # ========== МЕТОДЫ ДЛЯ ОБНОВЛЕНИЯ СЧЕТЧИКОВ ==========

    def update_counts(self):
        """Обновляет все счетчики"""
        from ideas.models import Idea

        self.followers_count = self.followers.count()
        self.following_count = self.follows.count()
        self.friends_count = self.get_friends().count()
        self.ideas_count = Idea.objects.filter(author=self.user).count()

        # Сохраняем только измененные поля
        self.save(update_fields=[
            'followers_count',
            'following_count',
            'friends_count',
            'ideas_count'
        ])

    # ========== МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ ==========

    def get_full_name(self):
        """Возвращает полное имя пользователя"""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username

    def get_relationship_status(self, profile):
        if profile.id == self.id:
            return 'self'
        if self.is_blocked(profile):
            return 'blocked'
        if self.is_blocked_by(profile):
            return 'blocked_by'
        if self.is_friend(profile):  # Использует is_friend(), а не поле friends
            return 'friend'
        if self.is_following(profile):
            return 'following'
        if self.is_follower(profile):
            return 'follower'
        return 'none'
    def get_social_links(self):
        """Возвращает словарь со ссылками на соцсети"""
        links = {}
        if self.website:
            links['website'] = self.website
        if self.github:
            links['github'] = self.github
        if self.telegram:
            links['telegram'] = f'https://t.me/{self.telegram}'
        if self.instagram:
            links['instagram'] = f'https://instagram.com/{self.instagram}'
        if self.twitter:
            links['twitter'] = f'https://twitter.com/{self.twitter}'
        if self.linkedin:
            links['linkedin'] = self.linkedin
        return links

    # ========== МЕТОДЫ ДЛЯ РЕКОМЕНДАЦИЙ ==========

    def get_suggestions(self, limit=5):
        """
        Рекомендации для подписки
        """
        # Исключаем себя, друзей, подписки и заблокированных
        exclude_ids = [self.id]
        exclude_ids.extend(self.follows.values_list('id', flat=True))
        exclude_ids.extend(self.get_friends().values_list('id', flat=True))
        exclude_ids.extend(self.blocked_users.values_list('id', flat=True))
        exclude_ids.extend(self.blocked_by.values_list('id', flat=True))

        # Находим профили с общими подписчиками
        suggestions = Profile.objects.exclude(
            id__in=exclude_ids
        ).annotate(
            mutual_follows_count=models.Count(
                'followers',
                filter=models.Q(followers__in=self.follows.all())
            )
        ).order_by('-mutual_follows_count', '-followers_count')[:limit]

        return suggestions

    def get_activity_feed(self, limit=20):
        """
        Возвращает идеи от друзей и подписок для ленты
        """
        from ideas.models import Idea

        # Получаем ID всех, на кого подписан и друзей
        interesting_ids = [self.id]
        interesting_ids.extend(self.get_friends().values_list('id', flat=True))
        interesting_ids.extend(self.follows.values_list('id', flat=True))

        # Исключаем заблокированных
        blocked_ids = self.blocked_users.values_list('user__id', flat=True)
        blocked_by_ids = self.blocked_by.values_list('user__id', flat=True)

        return Idea.objects.filter(
            author__profile__id__in=interesting_ids
        ).exclude(
            author__id__in=blocked_ids
        ).exclude(
            author__id__in=blocked_by_ids
        ).select_related('author').prefetch_related('likes')[:limit]


class Message(models.Model):
    """Личное сообщение между пользователями"""
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name='Получатель'
    )
    body = models.TextField('Текст', max_length=4000)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)
    read_at = models.DateTimeField('Прочитано', null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        indexes = [
            models.Index(fields=['sender', 'recipient', '-created_at']),
        ]

    def __str__(self):
        return f'{self.sender_id} → {self.recipient_id}: {self.body[:40]}'