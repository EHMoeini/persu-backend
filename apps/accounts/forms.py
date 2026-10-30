from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError

from .models import User


class UserCreationForm(forms.ModelForm):
    """Admin form for creating a user with a properly hashed password."""

    password1 = forms.CharField(
        label="Password", strip=False, widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Password confirmation", strip=False, widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("phone_e164", "nick_name", "avatar")

    def clean_password2(self) -> str:
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Admin form that displays the password hash without allowing edits."""

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text="Raw passwords are not stored, so there is no way to see this "
        "user's password, but you can change it using the password form.",
    )

    class Meta:
        model = User
        fields = (
            "phone_e164",
            "password",
            "nick_name",
            "avatar",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
