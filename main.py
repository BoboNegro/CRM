from fastapi import FastAPI
import requests

AIRTABLE_API_KEY = "pathvhQdTab7zjFET.5295a0f905ef13e9d6c6bba6e016deabcc51391180594d7db2b2d606e301804c"
AIRTABLE_BASE_ID = "appJ7uo2lPBUZT2CZ"
AIRTABLE_TABLE_ACCOUNTS = "accounts"
AIRTABLE_TABLE_PRODUCTS = "products"
AIRTABLE_TABLE_PIPELINE = "sales_pipeline"
AIRTABLE_TABLE_TEAM = "sales_team"
app = FastAPI()

def airtable_request(method, endpoint="", data=None, table_name=""):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.request(method, url, json=data, headers=headers)
    if not response.ok:
        raise Exception(f"Error {response.status_code}: {response.text}")
    return response.json()


#Traitement "LOGIN"


#Traitement "ACCOUNTS"
@app.get("/airtable/accounts/")
def get_airtable_data(table_name: str):
    try:
        data = airtable_request("GET", table_name=AIRTABLE_TABLE_ACCOUNTS)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


#Traitement "SALES"

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

#Traitement "PRODUCTS"

#Traitement "SALES"