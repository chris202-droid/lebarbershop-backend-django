"""
Catalogue par défaut appliqué automatiquement à chaque nouveau salon, pour
que le gestionnaire n'ait pas à ressaisir manuellement les soins et produits
de base d'un salon de coiffure/esthétique moderne (points 12 et 13 du
scénario socle). Il reste bien sûr libre de modifier, désactiver ou
compléter cette liste ensuite depuis son tableau de bord.
"""

# --- Soins par défaut : (nom, catégorie, prix FCFA, durée en minutes) ---
# Les catégories correspondent à Soin.Categorie (apps/services/models.py).
SOINS_PAR_DEFAUT = [
    # Coiffure homme
    ("Coupe simple", "coiffure_homme", 1500, 30),
    ("Coiffure avec black (design)", "coiffure_homme", 3000, 45),
    ("Dégradé américain", "coiffure_homme", 2000, 40),
    ("Coupe + barbe", "coiffure_homme", 2500, 40),
    ("Rasage complet", "coiffure_homme", 1500, 20),

    # Coiffure femme
    ("Brushing", "coiffure_femme", 3000, 45),
    ("Loxe (locks)", "coiffure_femme", 15000, 180),
    ("Tissage", "coiffure_femme", 12000, 120),
    ("Nattes collées", "coiffure_femme", 8000, 90),
    ("Nattes pareil", "coiffure_femme", 10000, 120),
    ("Défrisage", "coiffure_femme", 6000, 60),
    ("Coloration", "coiffure_femme", 10000, 90),
    ("Coupe femme", "coiffure_femme", 3000, 40),

    # Esthétique
    ("Soin du visage", "esthetique", 8000, 45),
    ("Épilation sourcils", "esthetique", 2000, 15),
    ("Maquillage jour", "esthetique", 10000, 45),
    ("Maquillage soirée", "esthetique", 15000, 60),

    # Manucure / pédicure
    ("Manucure simple", "manucure", 3000, 30),
    ("Manucure gel", "manucure", 6000, 60),
    ("Pédicure simple", "pedicure", 4000, 30),
    ("Pédicure spa", "pedicure", 7000, 60),
]

# --- Produits par défaut : (nom, catégorie, quantité initiale, seuil d'alerte, prix d'achat unitaire FCFA) ---
# Les catégories correspondent à Produit.Categorie (apps/stocks/models.py).
PRODUITS_PAR_DEFAUT = [
    # Matériel
    ("Tondeuse électrique", "materiel", 2, 1, 25000),
    ("Peigne afro", "materiel", 5, 2, 1000),
    ("Ciseaux de coupe", "materiel", 3, 1, 8000),
    ("Rasoir coupe-chou", "materiel", 3, 1, 3500),
    ("Séchoir à casque", "materiel", 1, 1, 45000),
    ("Lisseur à cheveux", "materiel", 2, 1, 15000),
    ("Brosse ronde chauffante", "materiel", 2, 1, 6000),
    ("Tabliers de protection", "materiel", 6, 2, 2000),

    # Produits homme
    ("Gel coiffant premium", "produit_homme", 10, 5, 1500),
    ("Mousse à raser", "produit_homme", 8, 3, 1200),
    ("Après-rasage", "produit_homme", 8, 3, 1500),
    ("Cire capillaire", "produit_homme", 6, 3, 2000),
    ("Shampoing homme", "produit_homme", 8, 3, 1800),

    # Produits femme
    ("Shampoing kératine", "produit_femme", 12, 5, 2500),
    ("Après-shampoing", "produit_femme", 10, 4, 2200),
    ("Crème coiffante", "produit_femme", 8, 3, 2000),
    ("Huile capillaire", "produit_femme", 8, 3, 1800),
    ("Coloration L'Oréal", "produit_femme", 10, 4, 3500),
    ("Défrisant", "produit_femme", 6, 3, 4000),
    ("Mèches / extensions", "produit_femme", 15, 5, 5000),
    ("Gel fixation nattes", "produit_femme", 8, 3, 1500),

    # Esthétique
    ("Crème visage", "esthetique", 8, 3, 3000),
    ("Vernis à ongles (assortiment)", "esthetique", 15, 5, 1000),
    ("Dissolvant", "esthetique", 6, 2, 1200),
    ("Coton démaquillant", "esthetique", 20, 8, 500),
    ("Huile de massage", "esthetique", 6, 2, 2500),
    ("Masque facial", "esthetique", 10, 4, 1800),
]


def appliquer_catalogue_par_defaut(salon):
    """
    Crée les soins et produits par défaut pour un salon — appelée à la
    création d'un nouveau salon, mais aussi rejouable sans risque sur un
    salon existant (point 5 : une évolution du catalogue par défaut doit
    pouvoir être rattrapée sur les salons déjà en base) : seuls les
    éléments dont le nom n'existe pas encore pour ce salon sont ajoutés,
    aucun doublon n'est créé.
    """
    from apps.services.models import Soin
    from apps.stocks.models import Produit

    noms_soins_existants = set(salon.soins.values_list("nom", flat=True))
    Soin.objects.bulk_create([
        Soin(salon=salon, nom=nom, categorie=categorie, prix=prix, duree_estimee_minutes=duree)
        for nom, categorie, prix, duree in SOINS_PAR_DEFAUT
        if nom not in noms_soins_existants
    ])

    noms_produits_existants = set(salon.produits.values_list("nom", flat=True))
    Produit.objects.bulk_create([
        Produit(salon=salon, nom=nom, categorie=categorie, quantite_stock=quantite,
                seuil_alerte=seuil, prix_unitaire_achat=prix_achat)
        for nom, categorie, quantite, seuil, prix_achat in PRODUITS_PAR_DEFAUT
        if nom not in noms_produits_existants
    ])
