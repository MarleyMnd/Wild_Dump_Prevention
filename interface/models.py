from django.db import models
from django.utils import timezone
from django.db import transaction
import os
from PIL import Image
import json
import matplotlib.pyplot as plt
import numpy as np


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

                    # Générer et sauvegarder l’histogramme RGB
                    self._generer_histogramme_couleur()
                    
                    # Générer et sauvegarder l’histogramme de luminance
                    self._generer_histogramme_luminance()

                    # Générer et sauvegarder les contours
                    self._generer_contours()
                    
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

    def _generer_histogramme_couleur(self, save_histograms=True):
        """
        Génère un histogramme RGB de l'image et le sauvegarde dans le dossier histogrammes_rgb.
        """
        try:
            with Image.open(self.image.path).convert("RGB") as image:
                np_image = np.array(image)

                r = np_image[:, :, 0].flatten()
                g = np_image[:, :, 1].flatten()
                b = np_image[:, :, 2].flatten()

                plt.figure(figsize=(8, 4))
                plt.hist(r, bins=256, color='red', alpha=0.5, label='Rouge')
                plt.hist(g, bins=256, color='green', alpha=0.5, label='Vert')
                plt.hist(b, bins=256, color='blue', alpha=0.5, label='Bleu')
                plt.title(f"Histogramme RVB - Image {self.id}")
                plt.xlabel("Valeur de pixel")
                plt.ylabel("Nombre de pixels")
                plt.legend()
                plt.tight_layout()

                if save_histograms:
                    histo_dir = os.path.join(os.path.dirname(self.image.path), "histogrammes_rgb")
                    os.makedirs(histo_dir, exist_ok=True)
                    histo_path = os.path.join(histo_dir, f"{os.path.splitext(os.path.basename(self.image.name))[0]}_hist.png")
                    plt.savefig(histo_path)
                    print(f"Histogramme RGB sauvegardé : {histo_path}")
                else:
                    plt.show()
                plt.close()
        except Exception as e:
            print(f"Erreur lors de la génération de l'histogramme : {e}")

    def _generer_histogramme_luminance(self, save_histograms=True):
        """
        Génère un histogramme de luminance (niveaux de gris) et le sauvegarde dans le dossier histogrammes_luminances.
        """
        try:
            with Image.open(self.image.path).convert("L") as image:
                np_image = np.array(image)

                plt.figure(figsize=(8, 4))
                plt.hist(np_image.flatten(), bins=256, range=(0, 255), color='gray', alpha=0.8)
                plt.title(f'Histogramme de luminance - Image {self.id}')
                plt.xlabel('Luminance (0 = noir, 255 = blanc)')
                plt.ylabel('Nombre de pixels')
                plt.grid(True)
                plt.tight_layout()

                if save_histograms:
                    histo_dir = os.path.join(os.path.dirname(self.image.path), "histogrammes_luminances")
                    os.makedirs(histo_dir, exist_ok=True)
                    histo_path = os.path.join(histo_dir, f"{os.path.splitext(os.path.basename(self.image.name))[0]}_luminance_hist.png")
                    plt.savefig(histo_path)
                    print(f"Histogramme de luminance sauvegardé : {histo_path}")
                else:
                    plt.show()
                plt.close()
        except Exception as e:
            print(f"Erreur lors de la génération de l'histogramme de luminance : {e}")

        import cv2  # Assure-toi d'importer OpenCV en haut du fichier

    def _generer_contours(self, save_contours=True):
        """
        Détecte les contours de l'image à l'aide de l'algorithme de Canny et les sauvegarde.
        """
        try:
            image_path = self.image.path
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                print(f"Impossible de lire l'image : {self.image.name}")
                return

            edges = cv2.Canny(image, threshold1=100, threshold2=200)

            plt.figure(figsize=(8, 6))
            plt.imshow(edges, cmap='gray')
            plt.title(f"Contours (Canny) - Image {self.id}")
            plt.axis('off')

            if save_contours:
                contours_dir = os.path.join(os.path.dirname(image_path), "contours")
                os.makedirs(contours_dir, exist_ok=True)
                save_path = os.path.join(contours_dir, f"{os.path.splitext(os.path.basename(self.image.name))[0]}_contours.png")
                cv2.imwrite(save_path, edges)
                print(f"Contours sauvegardés : {save_path}")
            else:
                plt.show()

            plt.close()
        except Exception as e:
            print(f"Erreur lors de la détection des contours : {e}")
