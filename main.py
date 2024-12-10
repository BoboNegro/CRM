from fastapi import FastAPI, HTTPException
import requests
import pandas as pd
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel
import os

AIRTABLE_API_KEY = "pathvhQdTab7zjFET.5295a0f905ef13e9d6c6bba6e016deabcc51391180594d7db2b2d606e301804c"
AIRTABLE_BASE_ID = "appJ7uo2lPBUZT2CZ"
AIRTABLE_TABLE_ACCOUNTS = "accounts"
AIRTABLE_TABLE_PRODUCTS = "products"
AIRTABLE_TABLE_PIPELINE = "sales_pipeline"
AIRTABLE_TABLE_TEAM = "sales_teams"
app = FastAPI()


class RevenueResponse(BaseModel):
    total_revenue: float


def airtable_request(data=None, table_name=""):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    records = []

    while url:
        try:
            response = requests.request("GET", url, json=data, headers=headers)
            response.raise_for_status()  # This will raise an exception for 4xx/5xx HTTP codes
            data = response.json()
            records.extend(data.get("records", []))
            url = data.get("offset", None)
            if url:
                url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?offset={url}"
        except requests.exceptions.HTTPError as http_err:
            # Catch HTTP errors and raise an HTTPException with detailed error info
            raise HTTPException(status_code=response.status_code,
                                detail=f"HTTP error occurred: {http_err} - {response.text}")
        except requests.exceptions.RequestException as req_err:
            # Catch all other types of requests errors (e.g., connection errors)
            raise HTTPException(status_code=500, detail=f"Request error occurred: {req_err}")

    return pd.json_normalize([record["fields"] for record in records])


# Récupérer toutes les données d'une table
def get_all_records(table_name):
    all_records = []
    offset = None
    while True:
        params = {"offset": offset} if offset else {}
        df = airtable_request(data=params, table_name=table_name)
        all_records.extend(df.to_dict("records"))
        offset = df.get("offset")
        if not offset:
            break
    return all_records



def save_data_to_csv():
    df = pd.DataFrame(get_all_records(AIRTABLE_TABLE_PIPELINE))
    df.to_csv('sales_pipelines.csv', index=False)


def check_data_csv():
    if os.path.exists('sales_pipelines.csv'):
        print("Données sauvegardées dans 'sales_pipelines.csv'")
        return True
    else:
        print("Les données existent déjà.")
        return False

def load_data_from_csv():
    if os.path.exists('sales_pipelines.csv'):
        return pd.read_csv('sales_pipelines.csv')
    else:
        raise FileNotFoundError("Le fichier 'sales_pipelines.csv' est manquant.")


def initialize_data():
    if not check_data_csv():
        save_data_to_csv()

@app.get("/{month}")
async def calculate_total_per_month_and_year(month: int):
    try:

        initialize_data()

        # Chargez les données depuis le CSV si elles existent
        df = load_data_from_csv()

        df['close_date'] = pd.to_datetime(df['close_date'])
        df['year'] = df['close_date'].dt.year
        df['month'] = df['close_date'].dt.month
        df['day'] = df['close_date'].dt.day

        filtered_data = df[df['month'] == month]

        sales_amount = filtered_data.groupby(['year', 'month'])['close_value'].sum().reset_index()

        df_json = sales_amount.to_json(orient='records')
        df_dict = json.loads(df_json)

        # Return the total revenue as a dictionary matching the Pydantic model
        return {"data": df_dict}
    except HTTPException as http_err:
        # Handle specific HTTP errors that may occur during the request
        return JSONResponse(status_code=http_err.status_code, content={"message": http_err.detail})
    except Exception as e:
        # Handle any unexpected errors
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/{month}/{day}")
async def calculate_total_per_day_month_and_year(month: int, day: int):
    try:

        initialize_data()

        # Chargez les données depuis le CSV si elles existent
        df = load_data_from_csv()

        df['close_date'] = pd.to_datetime(df['close_date'])
        df['year'] = df['close_date'].dt.year
        df['month'] = df['close_date'].dt.month
        df['day'] = df['close_date'].dt.day

        filtered_data = df[(df['month'] == month) & (df['day'] == day)]


        sales_amount = filtered_data.groupby(['year', 'month', 'day'])['close_value'].sum().reset_index()

        df_json = sales_amount.to_json(orient='records')
        df_dict = json.loads(df_json)

        # Return the total revenue as a dictionary matching the Pydantic model
        return {"data": df_dict}
    except HTTPException as http_err:
        # Handle specific HTTP errors that may occur during the request
        return JSONResponse(status_code=http_err.status_code, content={"message": http_err.detail})
    except Exception as e:
        # Handle any unexpected errors
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/cr/{month}/{day}")
async def calculate_conversion_rate_per_day_month_and_year(month: int, day: int):
    try:

        initialize_data()

        # Chargez les données depuis le CSV si elles existent
        df = load_data_from_csv()

        total_opportunities = len(df)
        won_opportunities = len(df[df['deal_stage'] == 'Won'])
        global_conversion_rate = won_opportunities / total_opportunities

        df['month'] = df['close_date'].dt.month

        monthly_conversion_rates = df.groupby('month').apply(lambda x: len(x[x['deal_stage'] == 'Won']) / len(x))

        df_json = monthly_conversion_rates.to_json(orient='records')
        df_dict = json.loads(df_json)

        # Return the total revenue as a dictionary matching the Pydantic model
        return {"data": [df_dict, global_conversion_rate]}
    except HTTPException as http_err:
        # Handle specific HTTP errors that may occur during the request
        return JSONResponse(status_code=http_err.status_code, content={"message": http_err.detail})
    except Exception as e:
        # Handle any unexpected errors
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})

@app.get("/op/{month}/{day}")
async def calculate_opportunities_per_day_month_and_year(month: int, day: int):
    try:
        # Initialisation des données
        initialize_data()
        df = load_data_from_csv()

        # Convertir 'engage_date' en format datetime si ce n'est pas déjà fait
        df['engage_date'] = pd.to_datetime(df['engage_date'])

        # Filtrage des données par mois et jour
        filtered_data = df[(df['engage_date'].dt.month == month) & (df['engage_date'].dt.day == day)]

        # Calcul du nombre total d'opportunités pour ce jour précis
        total_opportunities = len(filtered_data)

        filtered_data

        # Comptage des opportunités par mois et jour
        opportunities_per_day = filtered_data.groupby([filtered_data['engage_date'].dt.year, filtered_data['engage_date'].dt.month, filtered_data['engage_date'].dt.day])['opportunity_id'].count().reset_index(name='nombre_opportunites')

        opportunities_per_day.columns = ['year', 'month', 'day', 'nombre_opportunites']

        # Convertir les résultats en format JSON
        df_json = opportunities_per_day.to_json(orient='records')
        df_dict = json.loads(df_json)

        # Retourner les données sous forme de dictionnaire
        return {"data": df_dict}

    except HTTPException as http_err:
        # Gérer les erreurs HTTP spécifiques
        return JSONResponse(status_code=http_err.status_code, content={"message": http_err.detail})
    except Exception as e:
        # Gérer toutes les erreurs inattendues
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})


"""
@app.get("/")
async def calculate_total_per_month_and_year():
    try:

        df = pd.DataFrame(get_all_records(AIRTABLE_TABLE_ACCOUNTS))


        df['year_established'].value_counts()

        grouped = df.groupby('year_established')['account'].apply(list).reset_index()

        df_json = grouped.to_json(orient='records')
        df_dict = json.loads(df_json)



        # Return the total revenue as a dictionary matching the Pydantic model
        return {"data": df_dict}
    except HTTPException as http_err:
        # Handle specific HTTP errors that may occur during the request
        return JSONResponse(status_code=http_err.status_code, content={"message": http_err.detail})
    except Exception as e:
        # Handle any unexpected errors
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})
"""