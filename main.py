from fastapi import FastAPI, HTTPException
import requests
import pandas as pd
from fastapi.responses import JSONResponse
import json
from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel
import os

AIRTABLE_API_KEY = "pathvhQdTab7zjFET.5295a0f905ef13e9d6c6bba6e016deabcc51391180594d7db2b2d606e301804c"
AIRTABLE_BASE_ID = "appJ7uo2lPBUZT2CZ"
AIRTABLE_TABLE_PIPELINE = "sales_pipeline"



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



def save_data_to_json():
    records = get_all_records(AIRTABLE_TABLE_PIPELINE)
    file_path = "sales_pipelines.json"

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(records, json_file, ensure_ascii=False, indent=4)

    return file_path

def check_data_csv():
    if os.path.exists('sales_pipelines.json'):
        print("Données sauvegardées dans 'sales_pipelines.json'")
        return True
    else:
        print("Les données existent déjà.")
        return False

def load_data():
    file_path = "sales_pipelines.json"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier {file_path} est introuvable.")

    with open(file_path, "r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    return data


@app.get("/{month}/{day}")
async def calculate_total_per_day_month_and_year(month: int, day: int):
    try:
        data = load_data()
        totals = defaultdict(float)

        for row in data:
            close_date = datetime.strptime(row["close_date"], "%Y-%m-%d")
            if close_date.month == month and close_date.day == day:
                year = close_date.year
                totals[(year, month, day)] += float(row.get("close_value", 0))

        result = [{"year": year, "month": month, "day": day, "total_sales": total}
                  for (year, month, day), total in totals.items()]
        return {"data": result}
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"An error occurred: {str(e)}"})



