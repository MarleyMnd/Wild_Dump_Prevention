from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Avg, Sum, Max, Min
from django.core.paginator import Paginator
from .models import ImageAnnotation
from .forms import ImageUploadForm, AnnotationForm
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from .utils import geocoder_adresse
import matplotlib.pyplot as plt
from io import BytesIO
import json
from math import radians, sin, cos, sqrt, atan2
from collections import deque
from collections import defaultdict
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def upload_image(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image_annotation = form.save(commit=False)
            lat = form.cleaned_data.get('latitude')
            lon = form.cleaned_data.get('longitude')
            adresse = form.cleaned_data.get('localisation')
            if (lat is None or lon is None) and adresse:
                try:
                    lat, lon = geocoder_adresse(adresse)
                except Exception:
                    lat = lon = None
                    messages.warning(request, "Adresse enregistrée mais géocodage impossible – coordonnées absentes.")
            image_annotation.latitude = lat
            image_annotation.longitude = lon
            image_annotation.save()
            messages.success(request, f"Image uploadée avec succès ! ID : {image_annotation.id}")
            return redirect('annoter_image', image_id=image_annotation.id)
        messages.error(request, "Erreur lors de l’upload – vérifiez le formulaire.")
    else:
        form = ImageUploadForm()
    dernieres_images = ImageAnnotation.objects.order_by('-date_ajout')[:5]
    return render(request, 'interface/upload.html', {'form': form, 'dernieres_images': dernieres_images})

def annoter_image(request, image_id):
    image_annotation = get_object_or_404(ImageAnnotation, id=image_id)
    if request.method == 'POST':
        form = AnnotationForm(request.POST)
        if form.is_valid():
            image_annotation.annotation = form.cleaned_data['annotation']
            image_annotation.save()
            return redirect('dashboard')
    else:
        form = AnnotationForm(initial={'annotation': image_annotation.annotation})
    return render(request, 'interface/annoter.html', {'image_annotation': image_annotation, 'form': form})

def dashboard(request):
    total_images = ImageAnnotation.objects.count()
    images_pleines = ImageAnnotation.objects.filter(annotation='pleine').count()
    images_vides = ImageAnnotation.objects.filter(annotation='vide').count()
    images_non_annotees = ImageAnnotation.objects.filter(annotation='non_annotee').count()
    pourcentage_pleines = round((images_pleines / total_images) * 100, 1) if total_images else 0
    pourcentage_vides = round((images_vides / total_images) * 100, 1) if total_images else 0
    pourcentage_non_annotees = round((images_non_annotees / total_images) * 100, 1) if total_images else 0

    auto_pleines = ImageAnnotation.objects.filter(annotation_automatique='pleine').count()
    auto_vides = ImageAnnotation.objects.filter(annotation_automatique='vide').count()

    date_limite = datetime.now() - timedelta(days=7)
    images_recentes = ImageAnnotation.objects.filter(date_ajout__gte=date_limite).count()

    evolution_data = [
        {
            'date': (datetime.now() - timedelta(days=i)).strftime('%d/%m'),
            'count': ImageAnnotation.objects.filter(date_ajout__date=(datetime.now() - timedelta(days=i)).date()).count()
        }
        for i in range(6, -1, -1)
    ]

    images_list = ImageAnnotation.objects.all()
    paginator = Paginator(images_list, 10)
    page_number = request.GET.get('page')
    images = paginator.get_page(page_number)

    tailles = ImageAnnotation.objects.aggregate(
        taille_moyenne=Avg('taille_fichier'),
        taille_totale=Sum('taille_fichier'),
        taille_max=Max('taille_fichier'),
        taille_min=Min('taille_fichier'),
    )
    taille_moyenne = round(tailles['taille_moyenne'] or 0, 2)
    taille_totale = round(tailles['taille_totale'] or 0, 2)
    taille_max = round(tailles['taille_max'] or 0, 2)
    taille_min = round(tailles['taille_min'] or 0, 2)

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a)) * 1000  # en mètres

    points = list(ImageAnnotation.objects.filter(latitude__isnull=False, longitude__isnull=False).values(
    'id', 'latitude', 'longitude', 'annotation', 'date_ajout'))

    visited = set()
    zones = []
    rayon = 100  # mètres
    zone_id = 0

    for i, point in enumerate(points):
        if point['id'] in visited:
            continue

        cluster = []
        queue = deque([point])
        visited.add(point['id'])

        while queue:
            current = queue.popleft()
            cluster.append(current)

            for other in points:
                if other['id'] not in visited:
                    distance = haversine(current['latitude'], current['longitude'], other['latitude'], other['longitude'])
                    if distance <= rayon:
                        visited.add(other['id'])
                        queue.append(other)

        if len(cluster) >= 2:
            total = len(cluster)
            pleines = sum(1 for p in cluster if p['annotation'] == 'pleine')
            taux_pleines = pleines / total

            if taux_pleines > 0.6:
                zone_type = 'critique'
            elif taux_pleines > 0.3:
                zone_type = 'surveillee'
            else:
                zone_type = 'sure'

            for p in cluster:
                zones.append({
                    'id': p['id'],
                    'lat': p['latitude'],
                    'lng': p['longitude'],
                    'annotation': p['annotation'],
                    'zone_type': zone_type,
                    'zone_id': zone_id,
                    'date': p['date_ajout'].strftime('%d/%m/%Y %H:%M'),
                })

            zone_id += 1

        elif len(cluster) == 1:
            p = cluster[0]
            # Ajout de tous les points isolés, quelle que soit l'annotation
            if p['annotation'] == 'pleine':
                zone_type = 'critique'
            elif p['annotation'] == 'vide':
                zone_type = 'sure'
            else:
                zone_type = 'surveillee'
            zones.append({
                'id': p['id'],
                'lat': p['latitude'],
                'lng': p['longitude'],
                'annotation': p['annotation'],
                'zone_type': zone_type,
                'zone_id': zone_id,
                'date': p['date_ajout'].strftime('%d/%m/%Y %H:%M'),
            })
            zone_id += 1


    zone_type_counts = defaultdict(set)

    for z in zones:
        zone_type_counts[z['zone_type']].add(z['zone_id'])

    zones_critiques = len(zone_type_counts['critique'])
    zones_surveillees = len(zone_type_counts['surveillee'])
    zones_sures = len(zone_type_counts['sure'])

    coords_json = json.dumps(zones)

    return render(request, 'interface/dashboard.html', {
        'total_images': total_images,
        'images_pleines': images_pleines,
        'images_vides': images_vides,
        'images_non_annotees': images_non_annotees,
        'images_recentes': images_recentes,
        'stats_annotation': json.dumps({
            'pleines': images_pleines,
            'vides': images_vides,
            'non_annotees': images_non_annotees,
        }),
        'stats_auto': json.dumps({
            'pleines': auto_pleines,
            'vides': auto_vides,
            'non_annotees': total_images - auto_pleines - auto_vides,
        }),
        'evolution_data': json.dumps(evolution_data),
        'images': images,
        'pourcentage_pleines': pourcentage_pleines,
        'pourcentage_vides': pourcentage_vides,
        'pourcentage_non_annotees': pourcentage_non_annotees,
        'taille_moyenne': taille_moyenne,
        'taille_totale': taille_totale,
        'taille_max': taille_max,
        'taille_min': taille_min,
        'coords_json': coords_json,
        'zones_critiques': zones_critiques,
        'zones_surveillees': zones_surveillees,
        'zones_sures': zones_sures,
    })

def liste_images(request):
    images_list = ImageAnnotation.objects.all()
    filtre_annotation = request.GET.get('annotation')
    if filtre_annotation and filtre_annotation != 'toutes':
        images_list = images_list.filter(annotation=filtre_annotation)
    filtre_auto = request.GET.get('auto')
    if filtre_auto and filtre_auto != 'toutes':
        images_list = images_list.filter(annotation_automatique=filtre_auto)
    paginator = Paginator(images_list, 12)
    page_number = request.GET.get('page')
    images = paginator.get_page(page_number)
    return render(request, 'interface/liste_images.html', {
        'images': images,
        'filtre_annotation': filtre_annotation,
        'filtre_auto': filtre_auto,
    })

def api_stats(request):
    stats = {
        'total': ImageAnnotation.objects.count(),
        'pleines': ImageAnnotation.objects.filter(annotation='pleine').count(),
        'vides': ImageAnnotation.objects.filter(annotation='vide').count(),
        'non_annotees': ImageAnnotation.objects.filter(annotation='non_annotee').count(),
    }
    return JsonResponse(stats)

def stats_plot(request):
    labels = ['Pleine', 'Vide', 'Non annotée']
    counts = [
        ImageAnnotation.objects.filter(annotation='pleine').count(),
        ImageAnnotation.objects.filter(annotation='vide').count(),
        ImageAnnotation.objects.filter(annotation='non_annotee').count(),
    ]
    fig, ax = plt.subplots()
    if sum(counts) == 0:
        ax.text(0.5, 0.5, 'Aucune donnée disponible', horizontalalignment='center', verticalalignment='center', fontsize=14, transform=ax.transAxes)
        ax.axis('off')
    else:
        ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        plt.title("Répartition des annotations")
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='image/png')

def metrics_view(request):
    # Récupérer les images annotées manuellement
    queryset = ImageAnnotation.objects.exclude(annotation='non_annotee')
    y_true = [img.annotation for img in queryset]
    y_pred = [img.annotation_automatique for img in queryset]
    
    if not y_true:
        return render(request, 'interface/metrics.html', {
            'total_evaluated': 0,
            'error': "Aucune image annotée disponible pour le calcul"
        })

    # Calculer l'accuracy séparément
    accuracy = accuracy_score(y_true, y_pred)
    
    # Calculer le rapport de classification
    report = classification_report(y_true, y_pred, 
                                   labels=['pleine', 'vide'],
                                   output_dict=True,
                                   zero_division=0)
    
    # Extraire les métriques spécifiques
    metrics = {
        'accuracy': round(accuracy, 3),
        'precision_pleine': round(report['pleine']['precision'], 3),
        'recall_pleine': round(report['pleine']['recall'], 3),
        'f1_pleine': round(report['pleine']['f1-score'], 3),
        'precision_vide': round(report['vide']['precision'], 3),
        'recall_vide': round(report['vide']['recall'], 3),
        'f1_vide': round(report['vide']['f1-score'], 3),
    }
    
    # Matrice de confusion
    cm = confusion_matrix(y_true, y_pred, labels=['pleine', 'vide'])
    tn, fp, fn, tp = cm.ravel()
    
    context = {
        'total_evaluated': len(y_true),
        'metrics': metrics,
        'confusion_matrix': {
            'true_positive': tp,
            'true_negative': tn,
            'false_positive': fp,
            'false_negative': fn
        }
    }
    
    return render(request, 'interface/metrics.html', context)