from fastapi import FastAPI, HTTPException
import requests
from fastapi.responses import JSONResponse
import json
from collections import defaultdict
from datetime import datetime, timedelta
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


@app.get("/products/{month}")
async def calculate_sales_per_month(month: int):
    try:
        data = load_data()
        daily_totals = defaultdict(float)
        current_month_total = 0
        previous_month_total = 0

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
            if close_date:
                # Calcul des ventes pour le mois actuel
                if close_date.month == month:
                    day = close_date.day
                    daily_totals[day] += float(row.get("close_value", 0))
                    current_month_total += float(row.get("close_value", 0))

                # Calcul des ventes pour le mois précédent
                if close_date.month == (month - 1):
                    previous_month_total += float(row.get("close_value", 0))

        # Calcul de l'évolution par rapport au jour précédent
        result = []
        previous_day_total = None

        for day in sorted(daily_totals.keys()):
            current_day_total = daily_totals[day]
            percentage_change_day = None

            if previous_day_total is not None:
                percentage_change_day = ((current_day_total - previous_day_total) / previous_day_total) * 100 if previous_day_total > 0 else None

            result.append({
                "day": day,
                "total_sales": current_day_total,
                "percentage_change_day": round(percentage_change_day, 2) if percentage_change_day is not None else None
            })

            previous_day_total = current_day_total

        # Calcul de l'évolution par rapport au mois précédent
        percentage_change_month = None
        if previous_month_total > 0:
            percentage_change_month = ((current_month_total - previous_month_total) / previous_month_total) * 100

        return {
            "data": result,
            "monthly_total": round(current_month_total, 2),
            "percentage_change_month": round(percentage_change_month, 1) if percentage_change_month is not None else None
        }

    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/product_stats/{product_name}/{month}")
async def calculate_product_stats(product_name: str, month: int):
    try:
        data = load_data()  # Remplacer par ton propre mécanisme de chargement des données
        daily_totals = defaultdict(float)
        current_month_total = 0
        previous_month_total = 0
        location_sales = defaultdict(float)  # Pour suivre les ventes par emplacement

        # Vérifier si product_name est une liste et utiliser son premier élément si c'est le cas
        if isinstance(product_name, list):
            product_name = product_name[0]

        for row in data:
            close_date = None
            product = row.get("product (from product)")  # Assure-toi que cette clé est correcte
            location = row.get("office_location (from account)")  # Assure-toi que cette clé est correcte

            # Vérifie si le produit correspond au nom donné
            if isinstance(product, str) and product_name.lower() not in product.lower():
                continue  # Si le produit ne correspond pas, on passe à la ligne suivante

            # Vérifie si la clé 'close_date' existe et si elle a une valeur valide
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    # Si la conversion échoue (format incorrect), on passe à la ligne suivante sans rien faire
                    continue

            # Si close_date est valide, on traite les ventes
            if close_date:
                # Calcul des ventes pour le mois actuel
                if close_date.month == month:
                    day = close_date.day
                    daily_totals[day] += float(row.get("close_value", 0))
                    current_month_total += float(row.get("close_value", 0))

                # Calcul des ventes pour le mois précédent
                if close_date.month == (month - 1):
                    previous_month_total += float(row.get("close_value", 0))

                # Suivi des ventes par emplacement (si besoin)
                if location:
                    if isinstance(location, list):
                        location = location[0]
                    location_sales[location] += float(row.get("close_value", 0))

        # Calcul de l'emplacement avec le plus de ventes
        top_location = max(location_sales, key=location_sales.get, default=None)
        top_location_sales = location_sales.get(top_location, 0)

        # Calcul de l'évolution par rapport au jour précédent
        result = []
        previous_day_total = None

        for day in sorted(daily_totals.keys()):
            current_day_total = daily_totals[day]
            percentage_change_day = None

            # Calcul de l'évolution journalière
            if previous_day_total is not None and previous_day_total > 0:
                percentage_change_day = ((current_day_total - previous_day_total) / previous_day_total) * 100

            result.append({
                "day": day,
                "total_sales": current_day_total,
                "percentage_change_day": round(percentage_change_day, 2) if percentage_change_day is not None else None
            })

            previous_day_total = current_day_total

        # Calcul de l'évolution par rapport au mois précédent
        percentage_change_month = None
        if previous_month_total > 0:
            percentage_change_month = ((current_month_total - previous_month_total) / previous_month_total) * 100

        return {
            "product_name": product_name,
            "data": result,
            "monthly_total": round(current_month_total, 2),
            "percentage_change_month": round(percentage_change_month, 1) if percentage_change_month is not None else None,
            "top_location": top_location,
            "top_location_sales": round(top_location_sales, 2)
        }

    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/sales_status/{month}")
async def calculate_sales_status(month: int):
    try:
        data = load_data()

        # Variables pour compter les ventes par statut
        closed_sales_total = 0
        in_progress_sales_total = 0
        lost_sales_total = 0

        current_month_total = 0

        for row in data:
            close_date = None
            sale_status = row.get("status", "").lower()  # Statut de la vente (closed, in_progress, lost)

            # Vérifie si la vente a une date de clôture et si elle correspond au mois
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    # Si la conversion échoue (format incorrect), on passe à la ligne suivante sans rien faire
                    continue

            # Si close_date est valide et correspond au mois donné
            if close_date and close_date.month == month:
                sale_value = float(row.get("close_value", 0))
                current_month_total += sale_value

                # Filtrer par statut
                if sale_status == "closed":
                    closed_sales_total += sale_value
                elif sale_status == "in_progress":
                    in_progress_sales_total += sale_value
                elif sale_status == "lost":
                    lost_sales_total += sale_value

        # Retourner les résultats sous forme de JSON
        return {
            "month": month,
            "current_month_total": round(current_month_total, 2),
            "closed_sales_total": round(closed_sales_total, 2),
            "in_progress_sales_total": round(in_progress_sales_total, 2),
            "lost_sales_total": round(lost_sales_total, 2)
        }

    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/sales/conversion_rate/{month}")
async def calculate_conversion_rate_for_month(month: int):
    try:
        data = load_data()

        daily_opportunities = defaultdict(int)
        daily_conversions = defaultdict(int)
        monthly_opportunities = 0
        monthly_conversions = 0
        previous_month_opportunities = 0
        previous_month_conversions = 0

        for row in data:
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")

                    # Calcul des données pour le mois actuel
                    if close_date.month == month:
                        day = close_date.day
                        daily_opportunities[day] += 1
                        if row.get('deal_stage') == 'Won':
                            daily_conversions[day] += 1
                        monthly_opportunities += 1
                        if row.get('deal_stage') == 'Won':
                            monthly_conversions += 1

                    # Calcul des données pour le mois précédent
                    if close_date.month == (month - 1):
                        previous_month_opportunities += 1
                        if row.get('deal_stage') == 'Won':
                            previous_month_conversions += 1

                except ValueError:
                    continue

        # Calcul des taux de conversion journaliers
        daily_conversion_rates = []
        previous_day_conversion_rate = None

        for day in sorted(daily_opportunities.keys()):
            opportunities = daily_opportunities[day]
            conversions = daily_conversions[day]
            conversion_rate = (conversions / opportunities) * 100 if opportunities > 0 else None

            # Calcul de l'évolution par rapport au jour précédent
            percentage_change_day = None
            if previous_day_conversion_rate is not None and conversion_rate is not None:
                percentage_change_day = (
                                                (
                                                            conversion_rate - previous_day_conversion_rate) / previous_day_conversion_rate
                                        ) * 100

            daily_conversion_rates.append({
                "day": day,
                "conversion_rate": round(conversion_rate, 2) if conversion_rate is not None else None,
                "percentage_change_day": round(percentage_change_day, 2) if percentage_change_day is not None else None
            })

            # Mise à jour du taux de conversion du jour précédent
            previous_day_conversion_rate = conversion_rate

        # Calcul du taux de conversion mensuel
        monthly_conversion_rate = (
            (monthly_conversions / monthly_opportunities) * 100
            if monthly_opportunities > 0
            else None
        )

        # Calcul de l'évolution par rapport au mois précédent
        previous_month_conversion_rate = (
            (previous_month_conversions / previous_month_opportunities) * 100
            if previous_month_opportunities > 0
            else None
        )
        percentage_change_month = None
        if previous_month_conversion_rate is not None and monthly_conversion_rate is not None:
            percentage_change_month = (
                                              (monthly_conversion_rate - previous_month_conversion_rate)
                                              / previous_month_conversion_rate
                                      ) * 100

        return {
            "daily_conversion_rates": daily_conversion_rates,
            "monthly_conversion_rate": round(monthly_conversion_rate,
                                             2) if monthly_conversion_rate is not None else None,
            "percentage_change_month": round(percentage_change_month,
                                             2) if percentage_change_month is not None else None
        }

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


###############################################################

@app.get("/deals/{day}/{month}")
async def get_deals_by_day(day: int, month: int):
    try:
        data = load_data()
        lost_deals = 0
        won_deals = 0

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date:
                if close_date.month == month and close_date.day == day:
                    if row["deal_stage"] == "Lost":
                        print("Lost")
                        lost_deals += 1
                    elif row["deal_stage"] == "Won":
                        won_deals += 1

        return{
            "lost_deals": lost_deals,
            "won_deals": won_deals,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/deals/{month}")
async def get_deals_by_month(month: int):
    try:
        data = load_data()
        daily_deals = defaultdict(lambda: {"lost": 0, "won": 0})

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                day = close_date.day
                if row.get("deal_stage") == "Lost":
                    daily_deals[day]["lost"] += 1
                elif row.get("deal_stage") == "Won":
                    daily_deals[day]["won"] += 1

        result = [
            {"day": day, "lost_deals": deals["lost"], "won_deals": deals["won"]}
            for day, deals in sorted(daily_deals.items())
        ]

        return {"month": month, "daily_deals": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/agents/{month}")
async def get_sales_by_month(month: int):
    try:
        data = load_data()
        agent_stats = defaultdict(lambda: {"won_deals": 0, "total_deals": 0, "total_sales": 0.0})

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                agent_name = row.get("sales_agent (from sales_agent)")
                if isinstance(agent_name, list):
                    agent_name = agent_name[0]
                deal_stage = row.get("deal_stage")
                close_value = float(row.get("close_value", 0))

                agent_stats[agent_name]["total_deals"] += 1
                agent_stats[agent_name]["total_sales"] += close_value

                if deal_stage == "Won":
                    agent_stats[agent_name]["won_deals"] += 1

        result = [
            {
                "agent_name": agent,
                "won_deals": stats["won_deals"],
                "success_rate": round((stats["won_deals"] / stats["total_deals"] * 100), 2) if stats["total_deals"] > 0 else 0.0,
                "total_sales": round(stats["total_sales"], 2)
            }
            for agent, stats in agent_stats.items()
        ]

        return {"month": month, "agent_stats": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/top-agent/sales/{month}")
async def get_top_agent_by_month(month: int):
    try:
        data = load_data()
        agent_sales = defaultdict(float)

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                agent_name = row.get("sales_agent (from sales_agent)")
                if isinstance(agent_name, list):
                    agent_name = agent_name[0]
                close_value = float(row.get("close_value", 0))
                agent_sales[agent_name] += close_value

        if not agent_sales:
            return {"month": month, "top_agent": None}

        top_agent = max(agent_sales, key=agent_sales.get)
        return {
            "month": month,
            "top_agent": {
                "agent_name": top_agent,
                "total_sales": round(agent_sales[top_agent], 2)
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/top-agent/conv_rate/{month}")
async def get_top_agent_inconversion_by_month(month: int):
    try:
        data = load_data()
        agent_data = defaultdict(lambda: {"Won Deals": 0, "Total Opportunities": 0})

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                agent_name = row.get("sales_agent (from sales_agent)")
                if isinstance(agent_name, list):
                    agent_name = agent_name[0]

                deal_stage = row.get("deal_stage")

                if agent_name:
                    agent_data[agent_name]["Total Opportunities"] += 1
                    if deal_stage == "Won":
                        agent_data[agent_name]["Won Deals"] += 1

        if not agent_data:
            return {"month": month, "top_agent": None}

        top_agent = max(
            agent_data.items(),
            key=lambda item: (
                (item[1]["Won Deals"] / item[1]["Total Opportunities"])
                if item[1]["Total Opportunities"] > 0 else 0
            )
        )

        conversion_rate = (
            (top_agent[1]["Won Deals"] / top_agent[1]["Total Opportunities"] * 100)
            if top_agent[1]["Total Opportunities"] > 0 else 0
        )

        return {
            "month": month,
            "top_agent": {
                "agent_name": top_agent[0],
                "conversion_rate": round(conversion_rate, 2),
                "won_deals": top_agent[1]["Won Deals"],
                "total_opportunities": top_agent[1]["Total Opportunities"]
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/top-product/{month}")
async def get_top_product_by_month(month: int):
    try:
        data = load_data()  # Charger les données de manière appropriée
        product_sales_value = defaultdict(float)  # Pour accumuler la valeur des ventes
        product_sales_count = defaultdict(int)  # Pour compter le nombre de ventes

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            # Vérifier que la date correspond au mois spécifié
            if close_date and close_date.month == month:
                product_name = row.get("product (from product)")
                if isinstance(product_name, list):
                    product_name = product_name[0]

                # Récupérer la valeur de la vente
                sale_value = row.get("close_value", 0)

                if isinstance(sale_value, (int, float)):  # Assurer que la valeur de vente est numérique
                    product_sales_value[product_name] += sale_value
                    product_sales_count[product_name] += 1

        if not product_sales_value:
            return {"month": month, "top_product": None}

        # Trouver le produit ayant généré le plus de ventes en valeur
        top_product = max(product_sales_value, key=product_sales_value.get)

        return {
            "month": month,
            "top_product": {
                "product_name": top_product,
                "sales_value": round(product_sales_value[top_product], 2),  # Total des ventes
                "units_sold": product_sales_count[top_product]  # Nombre de fois vendu
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/top-customer/{month}")
async def get_top_customer_by_month(month: int):
    try:
        data = load_data()
        customer_stats = defaultdict(lambda: {"purchase_count": 0, "total_spent": 0.0})

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                customer_name = row.get("customer_name")
                if isinstance(customer_name, list):
                    customer_name = customer_name[0]
                close_value = float(row.get("close_value", 0))

                customer_stats[customer_name]["purchase_count"] += 1
                customer_stats[customer_name]["total_spent"] += close_value

        if not customer_stats:
            return {"month": month, "top_customer": None}

        top_customer = max(customer_stats, key=lambda customer: customer_stats[customer]["total_spent"])
        return {
            "month": month,
            "top_customer": {
                "customer_name": top_customer,
                "purchase_count": customer_stats[top_customer]["purchase_count"],
                "total_spent": round(customer_stats[top_customer]["total_spent"], 2)
            }
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/sales-by-location/{month}")
async def get_sales_by_location(month: int):
    try:
        data = load_data()
        location_sales = defaultdict(float)

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                location = row.get("office_location (from account)")
                if isinstance(location, list):
                    location = ", ".join(location)  # Convert list to comma-separated string
                elif location is None:
                    location = "Unknown"  # Default value for missing location

                close_value = float(row.get("close_value", 0))
                location_sales[location] += close_value

        result = [
            {"location": location, "total_sales": round(sales, 2)}
            for location, sales in sorted(location_sales.items(), key=lambda item: item[1], reverse=True)
        ]

        return {"month": month, "location_sales": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


@app.get("/top-locations/{month}")
async def get_top_locations_by_month(month: int):
    try:
        data = load_data()
        location_sales = defaultdict(float)

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                location = row.get("office_location (from account)")
                if isinstance(location, list):
                    location = location[0]
                close_value = float(row.get("close_value", 0))
                location_sales[location] += close_value

        result = [
            {"location": location, "total_sales": round(sales, 2)}
            for location, sales in sorted(location_sales.items(), key=lambda item: item[1], reverse=True)
        ]

        return {"month": month, "top_locations": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/sector-analysis/{month}/{parameter}")
async def get_sector_analysis(month: int, parameter: str):
    try:
        valid_parameters = {"Conversion Rate", "Won Deals", "Lost Deals", "Total Opportunities", "Total Sales"}
        if parameter not in valid_parameters:
            raise HTTPException(status_code=400, detail=f"Invalid parameter. Choose from: {', '.join(valid_parameters)}")

        data = load_data()
        sector_analysis = defaultdict(lambda: {"Won Deals": 0, "Lost Deals": 0, "Total Opportunities": 0, "Total Sales": 0.0})

        for row in data:
            close_date = None
            if "close_date" in row and row["close_date"]:
                try:
                    close_date = datetime.strptime(str(row["close_date"]), "%Y-%m-%d")
                except ValueError:
                    continue

            if close_date and close_date.month == month:
                sector = row.get("sector (from account)")
                if isinstance(sector, list):
                    sector = sector[0]
                deal_stage = row.get("deal_stage")
                close_value = float(row.get("close_value", 0))

                if deal_stage == "Won":
                    sector_analysis[sector]["Won Deals"] += 1
                    sector_analysis[sector]["Total Sales"] += close_value
                elif deal_stage == "Lost":
                    sector_analysis[sector]["Lost Deals"] += 1

                sector_analysis[sector]["Total Opportunities"] += 1

        if parameter == "Conversion Rate":
            for sector, values in sector_analysis.items():
                total_opportunities = values["Total Opportunities"]
                won_deals = values["Won Deals"]
                if isinstance(won_deals, list):
                    won_deals = won_deals[0]
                values["Conversion Rate"] = round((won_deals / total_opportunities) * 100, 2) if total_opportunities > 0 else 0.0

        result = [
            {"sector": sector, parameter: values.get(parameter, 0)}
            for sector, values in sector_analysis.items()
        ]

        return {"month": month, "parameter": parameter, "sector_analysis": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})
