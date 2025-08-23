from django.core.management.base import BaseCommand
from reclamations.models import Station

class Command(BaseCommand):
    help = 'Importe toutes les stations Agil depuis la liste officielle'

    def handle(self, *args, **options):
        #liste des stations 
        AGIL_STATIONS = [
    {'name': 'Station AGIL ARIANA', 'city': 'Ariana', 'code': 'AGIL001', 'address': 'Ariana Ville'},
    {'name': 'Station AGIL S.A. BOUKHTIOUA', 'city': 'Ariana', 'code': 'AGIL002', 'address': 'Ariana Ville'},
    {'name': 'Station AGIL ENNASR', 'city': 'Ariana', 'code': 'AGIL003', 'address': 'Ariana Ville'},
    {'name': 'Station AGIL M\'NIHLA', 'city': 'Ariana', 'code': 'AGIL004', 'address': 'Ariana Ville'},

    {'name': 'Station AGIL BEJA', 'city': 'Beja', 'code': 'AGIL005', 'address': 'Beja Ville'},
    {'name': 'Station AGIL GOUBELLAT', 'city': 'Beja', 'code': 'AGIL006', 'address': 'Goubellat'},

    {'name': 'Station AGIL PORT DE RADES', 'city': 'Ben Arous', 'code': 'AGIL007', 'address': 'Rades'},
    {'name': 'Station AGIL SORTIE SUD Z4', 'city': 'Ben Arous', 'code': 'AGIL008', 'address': 'Z4'},
    {'name': 'Station AGIL DJEBEL JELLOUD', 'city': 'Ben Arous', 'code': 'AGIL009', 'address': 'Djebel Jelloud'},
    {'name': 'Station AGIL BEN AROUS MC 34', 'city': 'Ben Arous', 'code': 'AGIL010', 'address': 'Ben Arous'},
    {'name': 'Station AGIL MORNEG', 'city': 'Ben Arous', 'code': 'AGIL011', 'address': 'Mornag'},

    {'name': 'Station AGIL GABES GP 1', 'city': 'Gabes', 'code': 'AGIL012', 'address': 'Gabes'},
    {'name': 'Station AGIL Gabes Jara', 'city': 'Gabes', 'code': 'AGIL013', 'address': 'Jara'},

    {'name': 'Station AGIL GAFSA', 'city': 'Gafsa', 'code': 'AGIL014', 'address': 'Gafsa'},
    {'name': 'Station AGIL Metlaoui', 'city': 'Gafsa', 'code': 'AGIL015', 'address': 'Metlaoui'},
    {'name': 'Station AGIL Moulares', 'city': 'Gafsa', 'code': 'AGIL016', 'address': 'Moulares'},

    {'name': 'Station AGIL Borj El AMRI', 'city': 'Manouba', 'code': 'AGIL017', 'address': 'Borj El Amri'},
    {'name': 'Station AGIL Ksar Said', 'city': 'Manouba', 'code': 'AGIL018', 'address': 'Ksar Said'},

    {'name': 'Station AGIL MEDENINE', 'city': 'Medenine', 'code': 'AGIL019', 'address': 'Medenine'},
    {'name': 'Station AGIL DJERBA H . SOUK', 'city': 'Medenine', 'code': 'AGIL020', 'address': 'Houmt Souk'},

    {'name': 'Station AGIL Sidi ALOUANE', 'city': 'Mahdia', 'code': 'AGIL021', 'address': 'Sidi Alouane'},
    {'name': 'Station AGIL MELLOULECH', 'city': 'Mahdia', 'code': 'AGIL022', 'address': 'Melloulech'},
    {'name': 'Station AGIL AUTOROUTE A1 PK192 EL JEM', 'city': 'Mahdia', 'code': 'AGIL023', 'address': 'Autoroute A1 PK192 El Jem'},
    {'name': 'Station AGIL OULED CHAMEKH', 'city': 'Mahdia', 'code': 'AGIL024', 'address': 'Ouled Chamakh'},

    {'name': 'Station AGIL Moknine', 'city': 'Monastir', 'code': 'AGIL025', 'address': 'Moknine'},
    {'name': 'Station AGIL Jemmal', 'city': 'Monastir', 'code': 'AGIL026', 'address': 'Jemmal'},
    {'name': 'Station AGIL Ouardanine', 'city': 'Monastir', 'code': 'AGIL027', 'address': 'Ouardanine'},
    {'name': 'Station AGIL Autoroute A1 menzel hayet', 'city': 'Monastir', 'code': 'AGIL028', 'address': 'Autoroute A1 Menzel Hayet'},

    {'name': 'Station AGIL EL M\'REZKA', 'city': 'Nabeul', 'code': 'AGIL029', 'address': 'El M\'rezka'},
    {'name': 'Station AGIL Menzel TEMIM', 'city': 'Nabeul', 'code': 'AGIL030', 'address': 'Menzel Temim'},
    {'name': 'Station AGIL Grombalia', 'city': 'Nabeul', 'code': 'AGIL031', 'address': 'Grombalia'},

    {'name': 'Station AGIL Kerkennah', 'city': 'Sfax', 'code': 'AGIL032', 'address': 'Kerkennah'},
    {'name': 'Station AGIL Aguereb', 'city': 'Sfax', 'code': 'AGIL033', 'address': 'Aguereb'},
    {'name': 'Station AGIL Bderna', 'city': 'Sfax', 'code': 'AGIL034', 'address': 'Bderna'},
    {'name': 'Station AGIL Port de Sfax', 'city': 'Sfax', 'code': 'AGIL035', 'address': 'Port de Sfax'},

    {'name': 'Station AGIL SILIANA', 'city': 'Siliana', 'code': 'AGIL036', 'address': 'Siliana Ville'},

    {'name': 'Station AGIL Kantaoui', 'city': 'Sousse', 'code': 'AGIL037', 'address': 'Kantaoui'},
    {'name': 'Station AGIL Kondar', 'city': 'Sousse', 'code': 'AGIL038', 'address': 'Kondar'},
    {'name': 'Station AGIL Autoroute (sidi khlifa)', 'city': 'Sousse', 'code': 'AGIL039', 'address': 'Sidi Khlifa'},
    {'name': 'Station AGIL Hammam Sousse', 'city': 'Sousse', 'code': 'AGIL040', 'address': 'Hammam Sousse'},
    {'name': 'Station AGIL Sahloul', 'city': 'Sousse', 'code': 'AGIL041', 'address': 'Sahloul'},

    {'name': 'Station AGIL TOZEUR', 'city': 'Tozeur', 'code': 'AGIL042', 'address': 'Tozeur Ville'},
    {'name': 'Station AGIL TOZEUR Rte GAFSA', 'city': 'Tozeur', 'code': 'AGIL043', 'address': 'Route Gafsa'},
    {'name': 'Station AGIL Degueche', 'city': 'Tozeur', 'code': 'AGIL044', 'address': 'Degueche'},
    {'name': 'Station AGIL NAFTA', 'city': 'Tozeur', 'code': 'AGIL045', 'address': 'Nafta'},

    {'name': 'Station AGIL l\'Aouina', 'city': 'Tunis', 'code': 'AGIL046', 'address': 'L\'Aouina'},
    {'name': 'Station AGIL LA GOULETTE', 'city': 'Tunis', 'code': 'AGIL047', 'address': 'La Goulette'},
    {'name': 'Station AGIL GAMMARTH', 'city': 'Tunis', 'code': 'AGIL048', 'address': 'Gammarth'},
    {'name': 'Station AGIL EZZOUHOUR', 'city': 'Tunis', 'code': 'AGIL049', 'address': 'Ezzouhour'},
    {'name': 'Station AGIL ENTREE SUD', 'city': 'Tunis', 'code': 'AGIL050', 'address': 'Entrée Sud'},
    {'name': 'Station AGIL BERGES DU LAC', 'city': 'Tunis', 'code': 'AGIL051', 'address': 'Berges du Lac'},

    {'name': 'Station AGIL Bir M\'CHERGA', 'city': 'Zaghouan', 'code': 'AGIL052', 'address': 'Bir M\'cherga'},
    {'name': 'Station AGIL EL FAHS', 'city': 'Zaghouan', 'code': 'AGIL053', 'address': 'Zaghouan Ville'},
]


        created_count = 0
        for station_data in AGIL_STATIONS:
            station, created = Station.objects.update_or_create(
                name=station_data['name'],
                defaults={
                    'city': station_data.get('city', ''),
                    'code': station_data.get('code', ''),
                    'address': station_data.get('address', ''),
                    'phone': station_data.get('phone', '70 000 000'),
                    'opening_hours': "24/7",
                    
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"Créée : {station.name}")

        self.stdout.write(
            self.style.SUCCESS(f'Import terminé : {created_count} nouvelles stations créées')
        )
