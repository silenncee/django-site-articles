from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Idea(models.Model):
    """
    Модель для идей/цитат с поддержкой музыки
    """
    title = models.CharField('Название', max_length=200)
    content = models.TextField('Содержание')
    image = models.ImageField('Картинка', upload_to='ideas/', blank=True, null=True)

    # Аудиофайл
    audio = models.FileField(
        'Аудиофайл',
        upload_to='audio/',
        blank=True,
        null=True,
        help_text='Загрузите MP3 файл (максимум 10MB)'
    )
    audio_title = models.CharField(
        'Название трека',
        max_length=200,
        blank=True,
        null=True,
        help_text='Например: "Bohemian Rhapsody - Queen"'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ideas',
        verbose_name='Автор'
    )

    likes = models.ManyToManyField(
        User,
        related_name='liked_ideas',
        blank=True,
        verbose_name='Лайки'
    )

    class Meta:
        ordering = ['-created_at']  # Сначала новые
        verbose_name = 'Идея'
        verbose_name_plural = 'Идеи'

    def __str__(self):
        return self.title[:50]

    def total_likes(self):
        """Возвращает количество лайков"""
        return self.likes.count()

    def has_audio(self):
        """Проверяет, есть ли аудиофайл"""
        return bool(self.audio)

    def audio_filename(self):
        """Возвращает имя файла без пути"""
        if self.audio:
            return self.audio.name.split('/')[-1]
        return ''


class Comment(models.Model):
    """
    Комментарии к идеям
    """
    idea = models.ForeignKey(
        Idea,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Идея'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    content = models.TextField('Текст комментария', max_length=1000)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    # Для ответов на комментарии
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Родительский комментарий'
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return f'{self.author.username}: {self.content[:30]}'

    def is_reply(self):
        """Проверяет, является ли комментарий ответом"""
        return self.parent is not None