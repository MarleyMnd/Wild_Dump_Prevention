from geopy.geocoders import Nominatim

def geocoder_adresse(adresse):
    geolocator = Nominatim(user_agent="geoapi")
    try:
        location = geolocator.geocode(adresse)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"[GEO] Erreur : {e}")
    return None, None
