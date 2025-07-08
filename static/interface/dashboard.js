document.addEventListener('DOMContentLoaded', function() {
    const coords = JSON.parse(document.getElementById('coords-data').textContent);
    const defaultLatLng = coords.length ? [coords[0].lat, coords[0].lng] : [48.8566, 2.3522];
    const map = L.map('mapid').setView(defaultLatLng, 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19,
    }).addTo(map);

    const greenIcon = new L.Icon({
        iconUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/green.png',
        shadowUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/msmarker.shadow.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
        shadowSize: [59, 32],
        shadowAnchor: [16, 32]
    });

    const redIcon = new L.Icon({
        iconUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/red.png',
        shadowUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/msmarker.shadow.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
        shadowSize: [59, 32],
        shadowAnchor: [16, 32]
    });

    const orangeIcon = new L.Icon({
        iconUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/orange.png',
        shadowUrl: 'https://maps.gstatic.com/mapfiles/ms2/micons/msmarker.shadow.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
        shadowSize: [59, 32],
        shadowAnchor: [16, 32]
    });

    let markers = [];
    let zones = [];

    function clearMap() {
        markers.forEach(m => map.removeLayer(m));
        markers = [];
        zones.forEach(z => map.removeLayer(z));
        zones = [];
    }

    function renderMarkers(filteredAnnotations, filteredZones) {
        clearMap();

        const clusterMap = new Map();

        coords.forEach(point => {
            const key = point.zone_id;
            if (!clusterMap.has(key)) {
                clusterMap.set(key, []);
            }
            clusterMap.get(key).push(point);
        });

        clusterMap.forEach((group, zone_id) => {
            if (group.length === 0) return;

            const zoneType = group[0].zone_type;
            if (!filteredZones.includes(zoneType)) return; // ✅ filtrer les zones

            let sumLat = 0,
                sumLng = 0;
            group.forEach(p => {
                sumLat += parseFloat(p.lat);
                sumLng += parseFloat(p.lng);
            });
            const centerLat = sumLat / group.length;
            const centerLng = sumLng / group.length;

            let fillColor = "rgba(0, 255, 0, 0.3)";
            if (zoneType === "critique") fillColor = "rgba(255, 0, 0, 0.3)";
            else if (zoneType === "surveillee") fillColor = "rgba(255, 165, 0, 0.3)";

            const radius = 30 + group.length * 20;

            const circle = L.circle([centerLat, centerLng], {
                radius: radius,
                color: null,
                fillColor: fillColor,
                fillOpacity: 0.4
            }).addTo(map);

            zones.push(circle);
        });

        // Ajout des marqueurs
        coords.forEach(point => {
            if (!filteredAnnotations.includes(point.annotation)) return;
            if (!filteredZones.includes(point.zone_type)) return; // ✅ filtrer les marqueurs selon zone aussi

            let icon = greenIcon;
            if (point.annotation === "pleine") icon = redIcon;
            else if (point.annotation === "non_annotee") icon = orangeIcon;

            const marker = L.marker([point.lat, point.lng], { icon }).addTo(map);
            marker.bindPopup(`
            <strong>ID :</strong> ${point.id}<br>
            <strong>Annotation :</strong> ${point.annotation}<br>
            <strong>Zone :</strong> ${point.zone_type}<br>
            <strong>Date :</strong> ${point.date}
        `);
            markers.push(marker);
        });
    }

    const zoneCheckboxes = document.querySelectorAll(".zone-filter");
    zoneCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            const activeZoneTypes = Array.from(zoneCheckboxes)
                .filter(c => c.checked)
                .map(c => c.value);

            renderMarkers(['pleine', 'vide', 'non_annotee'], activeZoneTypes);
        });
    });


    renderMarkers(['pleine', 'vide', 'non_annotee'], ['critique', 'surveillee', 'sure']);


    const stats = JSON.parse(document.getElementById('stats-data').textContent);
    const ctx = document.getElementById('chartAnnotations').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Pleines', 'Vides', 'Non annotées'],
            datasets: [{
                label: 'Nombre d’images',
                data: [stats.pleines, stats.vides, stats.non_annotees],
                backgroundColor: ['#ff6b6b', '#4ecdc4', '#ffa726'],
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                title: { display: false }
            },
            scales: {
                y: { beginAtZero: true, precision: 0 }
            }
        }
    });

    setTimeout(() => location.reload(), 300000);
});