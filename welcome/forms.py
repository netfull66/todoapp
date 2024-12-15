from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser,Project

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        for fieldname in ['username', 'email', 'password1', 'password2']:
            self.fields[fieldname].help_text = None
        self.fields['email'].required = True


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name','start_date', 'end_date']  # Include 'start_date' if it's not already

    # Optionally, you can set default values or widgets for 'start_date'
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
