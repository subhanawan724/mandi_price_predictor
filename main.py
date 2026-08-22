import json
import joblib
import pandas as pd
import requests
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from fastapi import HTTPException, status


PREDICTION_HISTORY = []


def clean_expired_history():
    global PREDICTION_HISTORY
    cutoff_time = datetime.now() - timedelta(days=7)
    
    
    PREDICTION_HISTORY = [
        record for record in PREDICTION_HISTORY 
        if record["created_at_dt"] >= cutoff_time
    ]


app = FastAPI(title="Mandi Trader Intelligence API")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_index():
    return FileResponse("static/index.html")

model1 = joblib.load("model1_spoilage_classifier.pkl")
model2 = joblib.load("model2_price_regressor.pkl")
model1_features = joblib.load("model1_features.pkl")
model2_features = joblib.load("model2_features.pkl")


with open("item_perishability_mapping.json", "r") as f:
  ITEM_PERISHABILITY_MAP = json.load(f)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_default_fallback_key")



def fetch_live_weather(city_name: str):
  url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_API_KEY}&units=metric"
  try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      temp_c = data["main"]["temp"]
      rain_mm = data.get("rain", {}).get("1h", 0.0)
      return temp_c, rain_mm
    return 28.0, 0.0
  except Exception:
    return 28.0, 0.0



app.mount("/static", StaticFiles(directory="static"), name="static")



ADMIN_CONFIG = {
    "fuel_price_pkr": 278.0,
    
}

ADMIN_SECRET_KEY = "Subhan@999"

class AdminSettingsUpdate(BaseModel):
  fuel_price_pkr:float
  secret_key: str


class MandiTraderRequest(BaseModel):
  item: str
  mandi_location: str
  wholesale_base_price: float
  avg_distance_km: float
  arrival_trucks: int
  demand_index: int
  



@app.get("/admin/config")
def get_admin_config():
  return ADMIN_CONFIG



@app.post("/admin/update-settings")
def update_admin_settings(req: AdminSettingsUpdate):
  if req.secret_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Admin Passcode! Access Denied."
        )
  
  ADMIN_CONFIG["fuel_price_pkr"] = req.fuel_price_pkr

  return {
      "status": "success",
      "message": "Admin settings updated successfully",
      "current_config": ADMIN_CONFIG,
  }


@app.post("/trader-predict")
def trader_predict(req: MandiTraderRequest):
  
  temp_c, rain_mm = fetch_live_weather(req.mandi_location)

  
  perishability = ITEM_PERISHABILITY_MAP.get(req.item, "Medium")

  

 
  raw_m1 = pd.DataFrame([{
      "Perishability_Type": perishability,
      "Temperature_C": temp_c,
      "Rainfall_MM": rain_mm,
      "Distance_KM": req.avg_distance_km,
  }])

  encoded_m1 = pd.get_dummies(raw_m1, columns=["Perishability_Type"])
  X1_input = encoded_m1.reindex(columns=model1_features, fill_value=0)
  predicted_risk = model1.predict(X1_input)[0]


  current_fuel_price = ADMIN_CONFIG["fuel_price_pkr"]

  raw_m2 = pd.DataFrame([{
      "Item": req.item,
      "Mandi_Location": req.mandi_location,
      "Wholesale_Base_Price": req.wholesale_base_price,
      "Fuel_Price_PKR": current_fuel_price,
      "Distance_KM": req.avg_distance_km,
      "Arrival_Trucks": req.arrival_trucks,
      "Demand_Index": req.demand_index,
      "Spoilage_Risk": predicted_risk,
  }])

  encoded_m2 = pd.get_dummies(
      raw_m2, columns=["Item", "Mandi_Location", "Spoilage_Risk"]
  )
  X2_input = encoded_m2.reindex(columns=model2_features, fill_value=0)
  predicted_price = model2.predict(X2_input)[0]

 
  trader_margin = float(predicted_price) - req.wholesale_base_price

  now_dt = datetime.now()

   
  history_entry = {
        "id": len(PREDICTION_HISTORY) + 1,
        "timestamp": now_dt.strftime("%Y-%m-%d %H:%M"),
        "created_at_dt": now_dt, 
        "item": req.item,
        "mandi": req.mandi_location,
        "wholesale_base_price": req.wholesale_base_price,
        "fuel_price": current_fuel_price,
        "avg_distance_km": req.avg_distance_km,
        "arrival_trucks": req.arrival_trucks,
        "demand_index": req.demand_index,
        "live_weather": {
            "temperature_c": temp_c,
            "rainfall_mm": rain_mm
        },
        "auto_detected_perishability": perishability,
        "predicted_spoilage_risk": str(predicted_risk),
        "predicted_retail_price_pkr": round(float(predicted_price), 2),
        "estimated_trader_margin_pkr": round(trader_margin, 2)
    }

  PREDICTION_HISTORY.append(history_entry)
  clean_expired_history()


 
  return {
      "item": req.item,
      "mandi": req.mandi_location,
      "auto_detected_perishability": perishability,
      "live_weather": {"temperature_c": temp_c, "rainfall_mm": rain_mm},
      "predicted_spoilage_risk": str(predicted_risk),
      "wholesale_base_price": req.wholesale_base_price,
      "predicted_retail_price_pkr": round(float(predicted_price), 2),
      "estimated_trader_margin_pkr": round(trader_margin, 2),
  }


@app.get("/analytics/history")
def get_prediction_history():
    
    clean_expired_history()
    
   
    clean_response = []
    for record in PREDICTION_HISTORY:
        item_copy = record.copy()
        item_copy.pop("created_at_dt", None)
        clean_response.append(item_copy)
        
    return clean_response
