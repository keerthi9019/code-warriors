from datetime import datetime, timedelta

# Define your items and their expiry dates
items = [
    {"name": "Milk", "expiry_date": "2025-09-25"},
    {"name": "Bread", "expiry_date": "2025-09-18"},
    {"name": "Yogurt", "expiry_date": "2025-09-17"},
    {"name": "Cheese", "expiry_date": "2025-09-30"},
]

# Function to get signal based on expiry date
def get_expiry_signal(expiry_str):
    today = datetime.today().date()
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    days_left = (expiry - today).days

    if days_left < 0:
        return "🔴 RED - Expired"
    elif days_left <= 2:
        return "🟠 YELLOW - Expiring Soon"
    else:
        return "🟢 GREEN - Safe"

# Check and print signals
for item in items:
    signal = get_expiry_signal(item["expiry_date"])
    print(f"Item: {item['name']} | Expiry: {item['expiry_date']} | Status: {signal}")