from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.http import HttpResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from .models import ImageAnnotation
from .forms import ImageUploadForm, AnnotationForm
import json
from datetime import datetime, timedelta

def upload_image(request):
    """Vue pour l'upload d'images"""
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image_annotation = form.save()
            messages.success(request, f'Image uploadée avec succès ! ID: {image_annotation.id}')
            return redirect('annoter_image', image_id=image_annotation.id)
        else:
            messages.error(request, 'Erreur lors de l\'upload. Vérifiez le formulaire.')
    else:
        form = ImageUploadForm()
    
    # Récupérer les dernières images pour affichage
    dernieres_images = ImageAnnotation.objects.all()[:5]
    
    context = {
        'form': form,
        'dernieres_images': dernieres_images,
    }
    return render(request, 'interface/upload.html', context)

def annoter_image(request, image_id):
    """Vue pour annoter une image"""
    image_annotation = get_object_or_404(ImageAnnotation, id=image_id)
    
    if request.method == 'POST':
        form = AnnotationForm(request.POST)
        if form.is_valid():
            image_annotation.annotation = form.cleaned_data['annotation']
            image_annotation.save()
            messages.success(request, 'Annotation sauvegardée avec succès !')
            return redirect('dashboard')
    else:
        form = AnnotationForm(initial={'annotation': image_annotation.annotation})
    
    context = {
        'image_annotation': image_annotation,
        'form': form,
    }
    return render(request, 'interface/annoter.html', context)

def dashboard(request):
    """Vue du tableau de bord avec statistiques"""
    # Statistiques générales
    total_images = ImageAnnotation.objects.count()
    images_pleines = ImageAnnotation.objects.filter(annotation='pleine').count()
    images_vides = ImageAnnotation.objects.filter(annotation='vide').count()
    images_non_annotees = ImageAnnotation.objects.filter(annotation='non_annotee').count()
    
    # Statistiques de classification automatique
    auto_pleines = ImageAnnotation.objects.filter(annotation_automatique='pleine').count()
    auto_vides = ImageAnnotation.objects.filter(annotation_automatique='vide').count()
    
    # Images récentes (7 derniers jours)
    date_limite = datetime.now() - timedelta(days=7)
    images_recentes = ImageAnnotation.objects.filter(date_ajout__gte=date_limite).count()
    
    # Données pour les graphiques
    stats_annotation = {
        'pleines': images_pleines,
        'vides': images_vides,
        'non_annotees': images_non_annotees,
    }
    
    stats_auto = {
        'pleines': auto_pleines,
        'vides': auto_vides,
        'non_annotees': total_images - auto_pleines - auto_vides,
    }
    
    # Evolution par jour (7 derniers jours)
    evolution_data = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        count = ImageAnnotation.objects.filter(
            date_ajout__date=date.date()
        ).count()
        evolution_data.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })
    evolution_data.reverse()
    
    # Liste des images avec pagination
    images_list = ImageAnnotation.objects.all()
    paginator = Paginator(images_list, 10)
    page_number = request.GET.get('page')
    images = paginator.get_page(page_number)
    
    context = {
        'total_images': total_images,
        'images_pleines': images_pleines,
        'images_vides': images_vides,
        'images_non_annotees': images_non_annotees,
        'images_recentes': images_recentes,
        'stats_annotation': json.dumps(stats_annotation),
        'stats_auto': json.dumps(stats_auto),
        'evolution_data': json.dumps(evolution_data),
        'images': images,
    }
    return render(request, 'interface/dashboard.html', context)

def liste_images(request):
    """Vue pour lister toutes les images avec filtres"""
    images_list = ImageAnnotation.objects.all()
    
    # Filtres
    filtre_annotation = request.GET.get('annotation')
    if filtre_annotation and filtre_annotation != 'toutes':
        images_list = images_list.filter(annotation=filtre_annotation)
    
    filtre_auto = request.GET.get('auto')
    if filtre_auto and filtre_auto != 'toutes':
        images_list = images_list.filter(annotation_automatique=filtre_auto)
    
    # Pagination
    paginator = Paginator(images_list, 12)
    page_number = request.GET.get('page')
    images = paginator.get_page(page_number)
    
    context = {
        'images': images,
        'filtre_annotation': filtre_annotation,
        'filtre_auto': filtre_auto,
    }
    return render(request, 'interface/liste_images.html', context)

def api_stats(request):
    """API pour récupérer les statistiques en JSON"""
    stats = {
        'total': ImageAnnotation.objects.count(),
        'pleines': ImageAnnotation.objects.filter(annotation='pleine').count(),
        'vides': ImageAnnotation.objects.filter(annotation='vide').count(),
        'non_annotees': ImageAnnotation.objects.filter(annotation='non_annotee').count(),
    }
    return JsonResponse(stats)
