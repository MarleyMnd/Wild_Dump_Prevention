from django.db import models
from django.utils import timezone
from django.db import transaction
import os
from PIL import Image
import json

class ImageAnnotation(models.Model):
    ETAT_CHOICES = [
        ('pleine', 'Pleine'),
        ('vide', 'Vide'),
        ('non_annotee', 'Non annotée'),
    ]
    
    # Informations de base
    image = models.ImageField(upload_to='poubelles/', verbose_name="Image")
    date_ajout = models.DateTimeField(default=timezone.now, verbose_name="Date d'ajout")
    annotation = models.CharField(
        max_length=20, 
        choices=ETAT_CHOICES, 
        default='non_annotee',
        verbose_name="État de la poubelle"
    )
    annotation_automatique = models.CharField(
        max_length=20, 
        choices=ETAT_CHOICES, 
        default='non_annotee',
        verbose_name="Classification automatique"
    )
    
    # Métadonnées extraites automatiquement
    taille_fichier = models.FloatField(null=True, blank=True, verbose_name="Taille (Ko)")
    largeur = models.IntegerField(null=True, blank=True, verbose_name="Largeur (px)")
    hauteur = models.IntegerField(null=True, blank=True, verbose_name="Hauteur (px)")
    couleur_moyenne_r = models.IntegerField(null=True, blank=True, verbose_name="Rouge moyen")
    couleur_moyenne_g = models.IntegerField(null=True, blank=True, verbose_name="Vert moyen")
    couleur_moyenne_b = models.IntegerField(null=True, blank=True, verbose_name="Bleu moyen")
    luminance_moyenne = models.FloatField(null=True, blank=True, verbose_name="Luminance moyenne")
    contraste = models.FloatField(null=True, blank=True, verbose_name="Niveau de contraste")
    
    # Données optionnelles pour la cartographie
    localisation = models.CharField(max_length=255, blank=True, verbose_name="Localisation")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Annotation d'image"
        verbose_name_plural = "Annotations d'images"
        ordering = ['-date_ajout']
    
    def __str__(self):
        return f"Image {self.id} - {self.annotation} ({self.date_ajout.strftime('%d/%m/%Y %H:%M')})"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        # Sauvegarder d'abord pour avoir le fichier
        super().save(*args, **kwargs)
        
        # Extraire les caractéristiques si pas déjà fait
        if self.image and not self.taille_fichier:
            self.extraire_caracteristiques()
            self.classifier_automatiquement()
            # Sauvegarder à nouveau avec les métadonnées
            super().save(*args, **kwargs)
    
    def extraire_caracteristiques(self):
        """Extrait automatiquement les caractéristiques de l'image"""
        if not self.image:
            return
            
        try:
            # Taille du fichier
            self.taille_fichier = round(self.image.size / 1024, 2)  # En Ko
            
            # Ouvrir l'image avec Pillow
            with Image.open(self.image.path) as img:
                # Dimensions
                self.largeur, self.hauteur = img.size
                
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculer la couleur moyenne
                pixels = list(img.getdata())
                if pixels:
                    r_total = sum(pixel[0] for pixel in pixels)
                    g_total = sum(pixel[1] for pixel in pixels)
                    b_total = sum(pixel[2] for pixel in pixels)
                    nb_pixels = len(pixels)
                    
                    self.couleur_moyenne_r = round(r_total / nb_pixels)
                    self.couleur_moyenne_g = round(g_total / nb_pixels)
                    self.couleur_moyenne_b = round(b_total / nb_pixels)
                    
                    # Calculer la luminance moyenne (formule standard)
                    self.luminance_moyenne = round(
                        0.299 * self.couleur_moyenne_r + 
                        0.587 * self.couleur_moyenne_g + 
                        0.114 * self.couleur_moyenne_b, 2
                    )
                    
                    # Calculer le contraste (différence max-min)
                    luminances = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixels]
                    self.contraste = round(max(luminances) - min(luminances), 2)
                    
        except Exception as e:
            print(f"Erreur lors de l'extraction des caractéristiques : {e}")
    
    def classifier_automatiquement(self):
        """Applique les règles de classification automatique"""
        if not all([self.luminance_moyenne, self.taille_fichier, self.contraste]):
            return
        
        # Règles de classification basées sur les caractéristiques
        # Règle 1: Image sombre + gros fichier = poubelle pleine
        if self.luminance_moyenne < 100 and self.taille_fichier > 500:
            self.annotation_automatique = 'pleine'
        # Règle 2: Image claire + petit fichier = poubelle vide
        elif self.luminance_moyenne > 150 and self.taille_fichier < 300:
            self.annotation_automatique = 'vide'
        # Règle 3: Contraste élevé peut indiquer des déchets visibles
        elif self.contraste > 100:
            self.annotation_automatique = 'pleine'
        else:
            self.annotation_automatique = 'non_annotee'
    
    @property
    def couleur_moyenne_hex(self):
        """Retourne la couleur moyenne en format hexadécimal"""
        if all([self.couleur_moyenne_r, self.couleur_moyenne_g, self.couleur_moyenne_b]):
            return f"#{self.couleur_moyenne_r:02x}{self.couleur_moyenne_g:02x}{self.couleur_moyenne_b:02x}"
        return "#000000"
