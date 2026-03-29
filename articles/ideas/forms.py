from django import forms
from .models import Idea, Comment

class IdeaForm(forms.ModelForm):
    """
    Форма для создания и редактирования идей с аудио
    """
    class Meta:
        model = Idea
        fields = ['title', 'content', 'image', 'audio', 'audio_title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название идеи'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Опишите вашу идею...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'audio': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'audio/mpeg,audio/mp3'
            }),
            'audio_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название трека и исполнитель'
            }),
        }
        labels = {
            'title': 'Название',
            'content': 'Содержание',
            'image': 'Изображение (необязательно)',
            'audio': 'MP3 файл',
            'audio_title': 'Название трека',
        }

class CommentForm(forms.ModelForm):
    """
    Форма для комментариев
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Напишите комментарий...'
            })
        }
        labels = {
            'content': ''
        }