from django.contrib import admin
from .models import ImageAnnotation

@admin.register(ImageAnnotation)
class ImageAnnotationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'image_thumbnail', 'annotation', 'annotation_automatique', 
        'date_ajout', 'taille_fichier', 'localisation'
    ]
    list_filter = ['annotation', 'annotation_automatique', 'date_ajout']
    search_fields = ['localisation']
    readonly_fields = [
        'date_ajout', 'taille_fichier', 'largeur', 'hauteur',
        'couleur_moyenne_r', 'couleur_moyenne_g', 'couleur_moyenne_b',
        'luminance_moyenne', 'contraste', 'annotation_automatique'
    ]
    
    def image_thumbnail(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return "Pas d'image"
    image_thumbnail.allow_tags = True
    image_thumbnail.short_description = 'Aperçu'
    
    fieldsets = (
        ('Image et Annotation', {
            'fields': ('image', 'annotation', 'annotation_automatique', 'localisation')
        }),
        ('Métadonnées', {
            'fields': (
                'date_ajout', 'taille_fichier', 'largeur', 'hauteur',
                'couleur_moyenne_r', 'couleur_moyenne_g', 'couleur_moyenne_b',
                'luminance_moyenne', 'contraste'
            ),
            'classes': ('collapse',)
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )
