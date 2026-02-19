import requests
from bs4 import BeautifulSoup
import math
import csv
import os
import sys 
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Encodage 
sys.encoding = 'utf-8'

BASE_URL = "https://www.used-renault-trucks.fr"
START_URL = BASE_URL


# ---------------------------
# Session avec retry
# ---------------------------
def create_session():
    session = requests.Session()

    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "keep-alive"
    })

    return session


session = create_session()


# ---------------------------
# CLI Arguments
# ---------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Truck scraper - Used Renault Trucks"
    )

    parser.add_argument(
        "date_folder",
        help="Folder name (ex: 2026_02_19)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent workers (default=5)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip brands already processed"
    )

    return parser.parse_args()


# ---------------------------
# Initialisation dossier
# ---------------------------
def init_output_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"[+] Dossier créé : {folder_name}")
    else:
        print(f"[i] Dossier existant : {folder_name}")

    return folder_name


# ---------------------------
# Télécharger une page
# ---------------------------
def download_page(url):
    print(f"Downloading: {url}")

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[ERROR] {url} -> {e}")
        return None


# ---------------------------
# Extraire total pages
# ---------------------------
def extract_total_pages(html):
    soup = BeautifulSoup(html, "html.parser")

    last_page = soup.select_one("li.last a")
    if last_page:
        try:
            return int(last_page.text.strip())
        except:
            return 1

    return 1


# ---------------------------
# Extraire les categories
# ---------------------------
def extract_brands(html):
    soup = BeautifulSoup(html, "html.parser")
    brands = []

    for a in soup.select(".vehicle-categories-filter a"):
        href = a.get("href")
        if href:
            if not href.startswith("http"):
                href = BASE_URL + href
            brands.append(href)

    return list(set(brands))


# ---------------------------
# Scraper la page détails d'une annonce
# ---------------------------
def scrape_details(link):
    html = download_page(link)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    price_tag = soup.select_one("div.typography-heading-2")  
    mileage_tag = soup.select_one("h1.typography-heading-2 div.typography-heading-4")

    return {
        "price": price_tag.text.strip() if price_tag else "",
        "mileage": mileage_tag.text.split("-")[0].strip() if mileage_tag else ""
    }


# ---------------------------
# Scraper les données
# ---------------------------
def scrape_page(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for item in soup.select("#plp-results #wrap-plp-list a"):

        title_tag = item.select_one("h2")
        cat_tag = item.select_one(".text-subtle")
        link = item.get("href")
        if not link:
            continue
        if not link.startswith("http"):
            link = BASE_URL + link

        if not title_tag:
            continue

        title = title_tag.text.strip()
        categorie = cat_tag.text.strip() if cat_tag else ""

        # Récupérer détails
        details = scrape_details(link)

        results.append({
            "title": title,
            "categorie": categorie,
            "link": link,
            **details
        })

    return results


# ---------------------------
# Sauvegarde temporaire
# ---------------------------
def save_temp_file(brand_name, rows, temp_folder):

    file_path = os.path.join(temp_folder, f"{brand_name}.tab")

    fieldnames = ["title", "categorie", "link", "price", "mileage"]

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(rows)

    return file_path



# ---------------------------
# Déduplication
# ---------------------------
def deduplicate(file_path):
    seen = set()
    unique_rows = []

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames  # <- prend toutes les colonnes existantes
        for row in reader:
            if row["link"] not in seen:
                seen.add(row["link"])
                unique_rows.append(row)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(unique_rows)



# ---------------------------
# Fusion globale
# ---------------------------
def merge_global(temp_folder):

    global_file = os.path.join(temp_folder, "extract.tab")

    with open(global_file, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out, delimiter="\t")
        writer.writerow(["title", "categorie", "link"])

        for file in os.listdir(temp_folder):
            if not file.endswith(".tab") or file == "extract.tab":
                continue

            with open(os.path.join(temp_folder, file), encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                next(reader)
                for row in reader:
                    writer.writerow(row)

    print(f"Fusion globale créée : {global_file}")


# ---------------------------
# Traitement d'une categorie
# ---------------------------
def process_brand(brand_url, temp_folder, workers, resume):

    brand_name = brand_url.rstrip("/").split("/")[-1]
    temp_file_path = os.path.join(temp_folder, f"{brand_name}.tab")

    if resume and os.path.exists(temp_file_path):
        print(f"[SKIP] {brand_name} déjà traité.")
        return

    print(f"\nProcessing: {brand_name}")

    first_html = download_page(brand_url)
    if not first_html:
        return

    total_pages = extract_total_pages(first_html)
    all_results = []

    def process_page(page_number):
        url = f"{brand_url}?page={page_number}"
        html = download_page(url)
        if not html:
            return []
        return scrape_page(html)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_page, page)
            for page in range(1, total_pages + 1)
        ]

        for future in as_completed(futures):
            all_results.extend(future.result())

    temp_file = save_temp_file(brand_name, all_results, temp_folder)
    deduplicate(temp_file)


# ---------------------------
# MAIN
# ---------------------------
def main():
    args = parse_arguments()

    output_folder = init_output_folder(args.date_folder)

    print("\nTéléchargement page de départ...")
    html = download_page(START_URL)

    if not html:
        print("Impossible de charger la page principale.")
        return

    print("Extraction des categories...")
    brands = extract_brands(html)

    for brand in brands:
        process_brand(
            brand,
            temp_folder=output_folder,
            workers=args.workers,
            resume=args.resume
        )

    print("\nFusion globale...")
    merge_global(output_folder)

    print("\nScraping terminé")


if __name__ == "__main__":
    main()
