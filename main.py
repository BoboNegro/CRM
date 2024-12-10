from fastapi import FastAPI, HTTPException
import requests
from fastapi.responses import JSONResponse
import json
from collections import defaultdict
from datetime import datetime
import math
import os


AIRTABLE_API_KEY = "pathvhQdTab7zjFET.5295a0f905ef13e9d6c6bba6e016deabcc51391180594d7db2b2d606e301804c"
AIRTABLE_BASE_ID = "appJ7uo2lPBUZT2CZ"
AIRTABLE_TABLE_PIPELINE = "sales_pipeline"

app = FastAPI()



def handle_nan(obj):
    """Remplace les NaN ou les valeurs infinies par None"""
    if isinstance(obj, dict):  # Si c'est un dictionnaire
        return {k: handle_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):  # Si c'est une liste
        return [handle_nan(i) for i in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):  # Si c'est un NaN ou infini
        return None  # Remplacer NaN/infini par None (null en JSON)
    else:
        return obj

def airtable_request(data=None, table_name=""):
    """Récupère les données depuis Airtable"""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    records = []

    while url:
        try:
            response = requests.request("GET", url, json=data, headers=headers)
            response.raise_for_status()  # Cette méthode lèvera une exception pour les codes HTTP 4xx/5xx
            data = response.json()
            records.extend(data.get("records", []))
            url = data.get("offset", None)
            if url:
                url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?offset={url}"
        except requests.exceptions.HTTPError as http_err:
            # En cas d'erreur HTTP, on lève une exception détaillée
            raise HTTPException(status_code=response.status_code,
                                detail=f"HTTP error occurred: {http_err} - {response.text}")
        except requests.exceptions.RequestException as req_err:
            # En cas d'autre erreur de requête (ex : connexion échouée)
            raise HTTPException(status_code=500, detail=f"Request error occurred: {req_err}")

    return [record["fields"] for record in records]  # Retourne uniquement les champs des enregistrements

def save_data_to_json():
    """Sauvegarde les données dans un fichier JSON"""
    records = airtable_request(table_name=AIRTABLE_TABLE_PIPELINE)
    file_path = "sales_pipelines.json"

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(records, json_file, ensure_ascii=False, indent=4)

    return file_path

def check_data():
    """Vérifie si les données existent déjà dans le fichier JSON"""
    if os.path.exists('sales_pipelines.json'):
        print("Données sauvegardées dans 'sales_pipelines.json'")
        return True
    else:
        print("Les données existent déjà.")
        return False

def load_data():
    """Charge les données depuis un fichier JSON"""
    file_path = "sales_pipelines.json"
    if not os.path.exists(file_path):
        save_data_to_json()
        raise FileNotFoundError(f"Le fichier {file_path} est introuvable.")

    with open(file_path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    return data

@app.get("/products/{month}/{day}")
async def calculate_sales_per_day_month_and_year(month: int, day: int):
    try:
        data = load_data()
        totals = defaultdict(float)

        for row in data:
            close_date = None

            # Vérifie si la clé 'close_date' existe et si elle a une valeur valide
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    # Si la conversion échoue (format incorrect), on passe à la ligne suivante sans rien faire
                    continue

            # Si close_date est valide, on traite les ventes
            if close_date and close_date.month == month and close_date.day == day:
                year = close_date.year
                totals[(year, month, day)] += float(row.get("close_value", 0))

        # Prépare les résultats sous forme de liste de dictionnaires
        result = [{"year": year, "month": month, "day": day, "total_sales": total}
                  for (year, month, day), total in totals.items()]
        return {"data": result}

    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})



@app.get("/sales/conversion_rate/{month}/{day}")
async def calculate_conversion_rate(month: int, day: int):
    try:
        data = load_data()

        opportunities = defaultdict(int)
        conversions = defaultdict(int)
        month_opportunities = defaultdict(int)
        month_conversions = defaultdict(int)

        for row in data:
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                    month_key = close_date.strftime('%Y-%m')
                    day_key = close_date.strftime('%Y-%m-%d')

                    # Calculs mensuels (pour tous les jours du mois)
                    if close_date.month == month:
                        month_opportunities[month_key] += 1
                        if row.get('deal_stage') == 'Won':
                            month_conversions[month_key] += 1

                    # Calculs quotidiens (pour le jour spécifié)
                    if close_date.month == month and close_date.day == day:
                        opportunities[day_key] += 1
                        if row.get('deal_stage') == 'Won':
                            conversions[day_key] += 1

                except ValueError:
                    continue

        conversion_rates = {
            'monthly': {},
            'daily': {}
        }

        for month_key, total in month_opportunities.items():
            if total > 0:
                rate = (month_conversions[month_key] / total) * 100
                conversion_rates['monthly'][month_key] = round(rate, 1)

        for day_key, total in opportunities.items():
            if total > 0:
                rate = (conversions[day_key] / total ) * 100
                conversion_rates['daily'][day_key] = round(rate, 1)

        return JSONResponse(content=conversion_rates)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/sales/volume/{month}")
async def get_sales_volume(month: int):
    try:
        data = load_data()

        # Dictionnaire pour stocker les ventes par catégorie de produit
        sales_by_product_name = defaultdict(float)

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                    # Filtrer par mois
                    if close_date.month == month:
                        # Traitement des ventes par catégorie de produit
                        product_name = row.get('product (from product)')
                        if isinstance(product_name, list):
                            product_name = product_name[0]  # Prend le premier élément si c'est une liste
                        sales_value = float(row.get('close_value', 0))
                        sales_by_product_name[product_name] += sales_value

                except ValueError:
                    continue

        # Convertir le résultat en format JSON
        result = {category: round(value, 2) for category, value in sales_by_product_name.items()}

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/sales/{category}/{month}")
async def get_sales_by_category(category: str, month: int):
    try:
        data = load_data()
        sales_by_product_category = defaultdict(float)

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                    if close_date.month == month:
                        if category == "Manager":
                            product_category = row.get('manager (from sales_agent)')
                            if isinstance(product_category, list):
                                product_category = product_category[0]
                            sales_value = float(row.get('close_value', 0))
                            sales_by_product_category[product_category] += sales_value
                        elif category == "Sales Agent":
                            product_category = row.get('sales_agent (from sales_agent)')
                            if isinstance(product_category, list):
                                product_category = product_category[0]
                            sales_value = float(row.get('close_value', 0))
                            sales_by_product_category[product_category] += sales_value
                        elif category == "Account":
                            product_category = row.get('account (from account)')
                            if isinstance(product_category, list):
                                product_category = product_category[0]
                            sales_value = float(row.get('close_value', 0))
                            sales_by_product_category[product_category] += sales_value
                except ValueError:
                    continue

        result = {
            category: value
            for category, value in sorted(
                sales_by_product_category.items(),
                key=lambda item: item[1],  # Trier par la valeur (value)
                reverse=True  # Ordre décroissant
            )
        }

        return JSONResponse(content=result)


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/regions/{month}")
async def get_sales_percentage_by_region(month: int):
    try:
        data = load_data()
        sales_by_region = defaultdict(float)
        total_sales_value = 0.0
        total_sales_count = 0
        percentage_by_region = defaultdict(float)

        # Calcul des ventes totales par région et du total global
        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                    if close_date.month == month:
                        region = row.get('regional_office (from sales_agent)')
                        if isinstance(region, list):
                            region = region[0]
                        sales_value = float(row.get('close_value', 0))
                        sales_by_region[region] += sales_value
                        total_sales_value += sales_value
                        total_sales_count += 1
                except ValueError:
                    continue

        # Calcul des pourcentages
        for region, value in sales_by_region.items():
            percentage_by_region[region] = (value / total_sales_value) * 100 if total_sales_value else 0

        # Création du résultat final
        results = {
            region: {
                "total_sales_value": sales_value,
                "sales_percentage": percentage_by_region[region]
            }
            for region, sales_value in sorted(
                sales_by_region.items(),
                key=lambda item: item[1],
                reverse=True
            )
        }

        return JSONResponse(content=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


