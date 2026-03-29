from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from ideas.models import Idea


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Автоматически создает профиль при регистрации пользователя"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняет профиль при сохранении пользователя"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


# Обновление счетчиков подписок
@receiver(m2m_changed, sender=Profile.follows.through)
def update_follow_counts(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Обновляет счетчики подписок при изменении"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.update_counts()

        # Обновляем счетчики у всех, кого коснулось изменение
        if pk_set:
            for profile_id in pk_set:
                try:
                    profile = Profile.objects.get(id=profile_id)
                    profile.update_counts()
                except Profile.DoesNotExist:
                    pass



# Обновление счетчиков блокировок
@receiver(m2m_changed, sender=Profile.blocked_users.through)
def update_blocked_counts(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Обновляет что-то при блокировке (можно добавить логику)"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.update_counts()

        if pk_set:
            for profile_id in pk_set:
                try:
                    profile = Profile.objects.get(id=profile_id)
                    profile.update_counts()
                except Profile.DoesNotExist:
                    pass


# Обновление счетчика идей
@receiver(post_save, sender=Idea)
def update_ideas_count_on_save(sender, instance, created, **kwargs):
    """Обновляет счетчик идей при создании"""
    if created and hasattr(instance.author, 'profile'):
        instance.author.profile.update_counts()


@receiver(post_delete, sender=Idea)
def update_ideas_count_on_delete(sender, instance, **kwargs):
    """Обновляет счетчик идей при удалении"""
    if hasattr(instance.author, 'profile'):
        instance.author.profile.update_counts()