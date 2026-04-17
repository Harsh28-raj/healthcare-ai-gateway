from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime, date
import uvicorn

app = FastAPI(title="Healthcare AI Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

MONGO_URL = "mongodb+srv://Amresh:amresh887@buymeachai.yz2y62f.mongodb.net/HealthCareAi?retryWrites=true&w=majority&appName=BuyMeAChai"
client = MongoClient(MONGO_URL)
db = client["HealthCareAi"]

@app.get("/user/profile/{user_id}")
def get_user_profile(user_id: str):
    latest_disease = db["disease_history"].find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_food_logs = list(db["food_logs"].find({
        "user_id": user_id,
        "timestamp": {"$gte": today_start}
    }))
    today_avg_score = (
        sum(log["health_score"] for log in today_food_logs) / len(today_food_logs)
        if today_food_logs else None
    )
    
    recent_medicines = list(db["medicine_logs"].find(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    ).limit(5))
    
    unread_alerts = list(db["alerts"].find({
        "user_id": user_id,
        "is_read": False
    }).sort("timestamp", -1))
    
    confidence = latest_disease.get("confidence", 0) if latest_disease else 0
    score = today_avg_score or 100
    if confidence > 0.75 or score < 40:
        risk_level = "High"
    elif confidence > 0.50 or score < 60:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    
    return {
        "user_id": user_id,
        "latest_disease": {
            "disease": latest_disease["disease"],
            "confidence": latest_disease["confidence"],
            "detected_on": latest_disease["timestamp"].strftime("%Y-%m-%d")
        } if latest_disease else None,
        "today_food_score": round(today_avg_score, 1) if today_avg_score else None,
        "risk_level": risk_level,
        "active_medicines": [m["medicine_name"] for m in recent_medicines],
        "unread_alerts": [
            {
                "type": a["type"],
                "message": a["message"],
                "timestamp": a["timestamp"].isoformat()
            } for a in unread_alerts
        ],
        "today_food_logs": [
            {
                "items": log["items"],
                "calories": log["calories"],
                "health_score": log["health_score"],
                "risk_flags": log["risk_flags"]
            } for log in today_food_logs
        ]
    }

@app.get("/user/summary/{user_id}")
def get_user_summary(user_id: str):
    latest_disease = db["disease_history"].find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    latest_food = db["food_logs"].find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    recent_medicines = list(db["medicine_logs"].find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(3))
    
    parts = []
    if latest_disease:
        parts.append(f"User has predicted {latest_disease['disease']} with {latest_disease['confidence']*100:.0f}% confidence.")
    if latest_food:
        parts.append(f"Latest food score is {latest_food['health_score']} with flags: {', '.join(latest_food['risk_flags'])}.")
        parts.append(f"Activity level: {latest_food['activity_level']}.")
    if recent_medicines:
        med_names = ', '.join([m['medicine_name'] for m in recent_medicines])
        parts.append(f"Recently scanned medicines: {med_names}.")
    
    summary = " ".join(parts) if parts else "No health data available for this user yet."
    
    return {"user_id": user_id, "summary": summary}

@app.get("/user/alerts/{user_id}")
def get_user_alerts(user_id: str):
    alerts = list(db["alerts"].find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(20))
    
    return {
        "user_id": user_id,
        "total": len(alerts),
        "alerts": [
            {
                "type": a["type"],
                "message": a["message"],
                "is_read": a["is_read"],
                "timestamp": a["timestamp"].isoformat()
            } for a in alerts
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
