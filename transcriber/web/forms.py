from django import forms
from .models import TranscriptionJob


class TranscriptionForm(forms.ModelForm):
    class Meta:
        model = TranscriptionJob
        fields = ['audio_file', 'speaker_count']
        widgets = {
            'speaker_count': forms.NumberInput(attrs={'min': 1, 'max': 10}),
        }
