# WDP Project – PinYourBin

Ce projet consiste à construire une plateforme web pour annoter, visualiser et surveiller des images de poubelles afin de détecter les zones à risque de débordement.

## 🔧 Fonctionnalités

### Niveau 1 – Basique (Must)
- Interface web avec :
- Upload et affichage des images
 - Annotation manuelle
- Extraction de caractéristiques de base : taille, dimensions, couleur moyenne
- Stockage dans une base de données SQLite
- Règles conditionnelles codées en dur pour classifier les zones
- Graphique statique avec `matplotlib`

### Niveau 2 – Intermédiaire (Should)
- Interface utilisateur fluide pour annoter les images avec navigation
- Visualisation des zones de débordement sur carte (Leaflet)
- Dashboard interactif avec graphiques dynamiques (`Chart.js`)
- Filtres interactifs (type de zone, annotation)

### Niveau 3 – Avancé (Could Have)
- Pagination des images récentes

## Installation

1. Cloner le projet :

```bash
git clone https://github.com/lo-riana/WDP_project.git
cd WDP_project
```

2. Créer un environnement virtuel (recommandé) :

```bash
python -m venv env
source env/bin/activate  # ou env\Scripts\activate sous Windows
```

3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

4. Lancer le serveur :

```bash
python manage.py runserver
```

## Aperçu

- Visualisation dynamique des annotations
- Carte des zones à risque (critique, surveillée, sûre)
- Filtres interactifs sur la carte
- Graphique statique généré en backend avec `matplotlib`

## Structure

- `interface/`: app principale
- `static/`: fichiers JS et CSS
- `templates/`: pages HTML
- `db.sqlite3`: base de données locale
- `media/`: images uploadées
