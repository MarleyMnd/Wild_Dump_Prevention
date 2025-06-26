from django import forms
from .models import ImageAnnotation

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = ImageAnnotation
        fields = ['image', 'localisation']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png',
            }),
            'localisation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Rue de la République, Paris',
            }),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Vérifier la taille (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("L'image ne peut pas dépasser 10MB.")
            
            # Vérifier le format
            if not image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise forms.ValidationError("Seuls les formats JPG, JPEG et PNG sont acceptés.")
        
        return image

class AnnotationForm(forms.Form):
    annotation = forms.ChoiceField(
        choices=ImageAnnotation.ETAT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
