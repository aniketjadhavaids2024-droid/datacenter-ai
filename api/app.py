from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import json
import numpy as np
import random
import time
from datetime import datetime
from typing import Optional
import os

app = FastAPI(
    title="DataCenter AI Energy API",
    description="AI-powered data center energy prediction and optimization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

model = pickle.load(open(os.path.join(ROOT_DIR, "model/model.pkl"), "rb"))
metadata = json.load(open(os.path.join(ROOT_DIR, "model/metadata.json")))

# Simulated historical data (last 24 readings)
history = []

class PredictRequest(BaseModel):
    cpu_usage: float
    temperature: float
    humidity: float
    cooling_usage: float
    server_workload: float
    hour: Optional[int] = None
    day_of_week: Optional[int] = None

def get_suggestions(cpu, temp, cooling, server_workload, predicted_power):
    suggestions = []
    severity = "normal"

    if temp > 30:
        suggestions.append({
            "icon": "🌡️",
            "title": "High Temperature Detected",
            "action": f"Reduce temperature setpoint by 2–3°C. Current: {temp:.1f}°C",
            "saving": "~8% energy reduction",
            "priority": "HIGH"
        })
        severity = "warning"

    if cpu < 35:
        suggestions.append({
            "icon": "💤",
            "title": "Idle Servers Detected",
            "action": f"Shut down or consolidate underutilized servers. CPU: {cpu:.1f}%",
            "saving": "~15% energy reduction",
            "priority": "HIGH"
        })
        severity = "warning"

    if cooling > 70:
        suggestions.append({
            "icon": "❄️",
            "title": "Excessive Cooling Load",
            "action": "Optimize airflow management and raise cooling setpoints",
            "saving": "~10% energy reduction",
            "priority": "MEDIUM"
        })

    if server_workload > 85:
        suggestions.append({
            "icon": "⚖️",
            "title": "Workload Imbalance",
            "action": "Redistribute workloads across available servers",
            "saving": "~5% energy reduction",
            "priority": "MEDIUM"
        })
        severity = "critical" if temp > 30 else "warning"

    if predicted_power > 300:
        suggestions.append({
            "icon": "⚡",
            "title": "High Energy Consumption",
            "action": "Schedule non-critical workloads to off-peak hours (10 PM – 6 AM)",
            "saving": "~12% energy reduction",
            "priority": "HIGH"
        })
        severity = "critical"

    if not suggestions:
        suggestions.append({
            "icon": "✅",
            "title": "System Operating Optimally",
            "action": "All parameters within normal range. Continue monitoring.",
            "saving": "Maintaining current efficiency",
            "priority": "LOW"
        })
        severity = "normal"

    return suggestions, severity

@app.get("/")
def root():
    return {
        "message": "DataCenter AI Energy Optimization API",
        "version": "1.0.0",
        "model_accuracy": f"{metadata['accuracy_pct']}%",
        "endpoints": ["/predict", "/live", "/history", "/stats", "/docs"]
    }

@app.post("/predict")
def predict(req: PredictRequest):
    now = datetime.now()
    hour = req.hour if req.hour is not None else now.hour
    dow = req.day_of_week if req.day_of_week is not None else now.weekday()

    features = [[
        hour, dow,
        req.cpu_usage, req.temperature, req.humidity,
        req.cooling_usage, req.server_workload
    ]]

    predicted_power = float(model.predict(features)[0])
    baseline_power = predicted_power * 1.15
    energy_saved = baseline_power - predicted_power
    saving_pct = (energy_saved / baseline_power) * 100

    suggestions, severity = get_suggestions(
        req.cpu_usage, req.temperature,
        req.cooling_usage, req.server_workload,
        predicted_power
    )

    result = {
        "timestamp": now.isoformat(),
        "predicted_power_kwh": round(predicted_power, 2),
        "baseline_power_kwh": round(baseline_power, 2),
        "energy_saved_kwh": round(energy_saved, 2),
        "saving_percentage": round(saving_pct, 1),
        "severity": severity,
        "suggestions": suggestions,
        "inputs": {
            "cpu_usage": req.cpu_usage,
            "temperature": req.temperature,
            "humidity": req.humidity,
            "cooling_usage": req.cooling_usage,
            "server_workload": req.server_workload
        },
        "model_info": {
            "accuracy": f"{metadata['accuracy_pct']}%",
            "mae": metadata['mae']
        }
    }

    # Store in history
    history.append({
        "timestamp": now.isoformat(),
        "power": round(predicted_power, 2),
        "cpu": req.cpu_usage,
        "temp": req.temperature,
        "severity": severity
    })
    if len(history) > 50:
        history.pop(0)

    return result

@app.get("/live")
def live_data():
    """Simulates real-time sensor data from data center"""
    now = datetime.now()
    hour = now.hour
    
    # Realistic simulation based on time of day
    base_cpu = 65 if 9 <= hour <= 18 else 38
    cpu = round(np.clip(np.random.normal(base_cpu, 12), 10, 98), 1)
    temp = round(np.clip(18 + (cpu / 100) * 15 + np.random.normal(0, 1.5), 18, 40), 1)
    humidity = round(np.clip(np.random.normal(50, 8), 30, 70), 1)
    cooling = round(np.clip((temp - 18) * 3 + np.random.normal(0, 4), 0, 100), 1)
    workload = round(np.clip(cpu * 0.88 + np.random.normal(0, 4), 10, 100), 1)

    features = [[hour, now.weekday(), cpu, temp, humidity, cooling, workload]]
    predicted_power = float(model.predict(features)[0])
    predicted_power = round(np.clip(predicted_power, 50, 600), 2)

    suggestions, severity = get_suggestions(cpu, temp, cooling, workload, predicted_power)

    data = {
        "timestamp": now.isoformat(),
        "cpu_usage": cpu,
        "temperature": temp,
        "humidity": humidity,
        "cooling_usage": cooling,
        "server_workload": workload,
        "predicted_power_kwh": predicted_power,
        "severity": severity,
        "top_suggestion": suggestions[0] if suggestions else None,
        "all_suggestions": suggestions,
        "carbon_kg": round(predicted_power * 0.82 / 1000, 4),
        "cost_inr": round(predicted_power * 8.5, 2)
    }

    # Add to history
    history.append({
        "timestamp": now.isoformat(),
        "power": predicted_power,
        "cpu": cpu,
        "temp": temp,
        "severity": severity
    })
    if len(history) > 50:
        history.pop(0)

    return data

@app.get("/history")
def get_history():
    return {"history": history, "count": len(history)}

@app.get("/stats")
def get_stats():
    return {
        "model": {
            "type": "Random Forest Regressor",
            "accuracy": f"{metadata['accuracy_pct']}%",
            "mae_kwh": metadata['mae'],
            "rmse_kwh": metadata['rmse'],
            "r2_score": metadata['r2'],
            "trained_on": f"{metadata['train_size']} samples"
        },
        "feature_importance": metadata['feature_importance'],
        "system": {
            "total_readings": len(history),
            "avg_power": round(np.mean([h['power'] for h in history]), 2) if history else 0,
            "peak_power": round(max([h['power'] for h in history]), 2) if history else 0,
        }
    }
