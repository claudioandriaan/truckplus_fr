# Truckplus_FR - Scraper de camions Renault d'occasion

## Description

Truckplus_FR est un scraper Python pour extraire les annonces de camions Renault d'occasion depuis [used-renault-trucks.fr](https://www.used-renault-trucks.fr).  
Le script récupère :

- Les catégories (marques / types de camions)  
- Toutes les annonces de chaque catégorie  
- Les détails de chaque annonce : prix, kilométrage, puissance, année  
- Fusionne les résultats dans un fichier `extract.tab`  

Le projet est prêt pour :  

- Exécution locale  
- Docker  
- GitHub Actions pour un scraping quotidien automatisé  

---

## 🔧 Prérequis

- Python 3.12+  
- Pip  
- Windows / Linux / macOS  

Dépendances Python :  

```bash
pip install -r requirements.txt
```

⚡ Utilisation locale
Lancer le scraper

```bash
python truckplus_fr.py YYYY_MM_DD
```

Options

--workers N : nombre de threads (par défaut 5)

--resume : ignorer les catégories déjà traitées pour reprendre un scrape interrompu

Exemple avec 8 threads et reprise :
```bash
python truckplus_fr.py 2026_02_19 --workers 8 --resume
```