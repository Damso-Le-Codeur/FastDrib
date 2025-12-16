from django import forms

class VerificationForm(forms.Form):
    email = forms.EmailField(label="Votre Email")
    access_code = forms.CharField(label="Code de sécurité (6 chiffres)", max_length=6)