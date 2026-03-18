#!/usr/bin/env python3
"""
Creates DynamoDB tables and loads synthetic travel data for the travel assistant.
Tables: exec-synthetic-flights, exec-synthetic-hotels, exec-synthetic-restaurants, exec-synthetic-attractions,
        exec-synthetic-weather, exec-loyalty-programs, exec-travel-reservations
"""

import boto3
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker

fake = Faker()
AWS_REGION = "us-east-1"
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

# ---------------------------------------------------------------------------
# Table schemas
# ---------------------------------------------------------------------------
TABLE_CONFIGS = {
    "exec-synthetic-flights": {
        "KeySchema": [{"AttributeName": "flight_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "flight_id", "AttributeType": "S"},
            {"AttributeName": "origin_destination", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "OriginDestinationIndex",
                "KeySchema": [{"AttributeName": "origin_destination", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-synthetic-hotels": {
        "KeySchema": [{"AttributeName": "hotel_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "hotel_id", "AttributeType": "S"},
            {"AttributeName": "city", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "CityIndex",
                "KeySchema": [{"AttributeName": "city", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-synthetic-restaurants": {
        "KeySchema": [{"AttributeName": "restaurant_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "restaurant_id", "AttributeType": "S"},
            {"AttributeName": "city", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "CityIndex",
                "KeySchema": [{"AttributeName": "city", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-synthetic-attractions": {
        "KeySchema": [{"AttributeName": "attraction_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "attraction_id", "AttributeType": "S"},
            {"AttributeName": "city", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "CityIndex",
                "KeySchema": [{"AttributeName": "city", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-synthetic-weather": {
        "KeySchema": [{"AttributeName": "weather_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "weather_id", "AttributeType": "S"},
            {"AttributeName": "city", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "CityIndex",
                "KeySchema": [{"AttributeName": "city", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-loyalty-programs": {
        "KeySchema": [{"AttributeName": "program_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "program_id", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "CategoryIndex",
                "KeySchema": [{"AttributeName": "category", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "exec-travel-reservations": {
        "KeySchema": [{"AttributeName": "reservation_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "reservation_id", "AttributeType": "S"},
            {"AttributeName": "user_email", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
            {"AttributeName": "created_date", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "UserEmailIndex",
                "KeySchema": [{"AttributeName": "user_email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "StatusIndex",
                "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "CreatedDateIndex",
                "KeySchema": [{"AttributeName": "created_date", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def create_table(table_name, config):
    try:
        params = {
            "TableName": table_name,
            "KeySchema": config["KeySchema"],
            "AttributeDefinitions": config["AttributeDefinitions"],
            "BillingMode": "PAY_PER_REQUEST",
        }
        if config.get("GlobalSecondaryIndexes"):
            params["GlobalSecondaryIndexes"] = config["GlobalSecondaryIndexes"]
        table = dynamodb.create_table(**params)
        print(f"  ✅ Created table: {table_name}")
        return table
    except Exception as e:
        if "ResourceInUseException" in str(e):
            print(f"  📋 Table {table_name} already exists")
            return dynamodb.Table(table_name)
        raise


def wait_for_tables():
    """Wait until all tables are ACTIVE."""
    client = boto3.client("dynamodb", region_name=AWS_REGION)
    for name in TABLE_CONFIGS:
        try:
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=name, WaiterConfig={"Delay": 3, "MaxAttempts": 40})
        except Exception:
            pass


def load_items(table_name, items):
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"  ✅ Loaded {len(items)} records → {table_name}")


# ---------------------------------------------------------------------------
# Data generators
# ---------------------------------------------------------------------------

CITIES = ["New York", "Paris", "London", "Tokyo", "Sydney", "Dubai", "Los Angeles", "Frankfurt"]
AIRPORTS = {"JFK": "New York", "LAX": "Los Angeles", "CDG": "Paris", "LHR": "London",
            "FRA": "Frankfurt", "NRT": "Tokyo", "SYD": "Sydney", "DXB": "Dubai"}
AIRLINES = ["American Airlines", "Delta", "United", "Air France", "British Airways", "Lufthansa"]
HOTEL_CHAINS = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Accor", "Best Western"]


def generate_flights(count=1000):
    flights = []
    codes = list(AIRPORTS.keys())
    for i in range(count):
        origin = random.choice(codes)
        destination = random.choice([c for c in codes if c != origin])
        airline = random.choice(AIRLINES)
        flights.append({
            "flight_id": f"FL{i+1:04d}",
            "airline": airline,
            "flight_number": f"{airline[:2].upper()}{random.randint(100, 9999)}",
            "origin": origin,
            "destination": destination,
            "origin_destination": f"{origin}-{destination}",
            "departure_time": fake.date_time_between(start_date="+1d", end_date="+365d").isoformat(),
            "duration_minutes": random.randint(120, 900),
            "price": Decimal(str(random.randint(200, 2000))),
            "currency": "USD",
            "family_friendly": random.choice([True, False]),
            "loyalty_miles": random.randint(500, 5000) if random.random() > 0.3 else 0,
            "meal_service": random.choice([True, False]),
            "wifi_available": random.choice([True, False]),
            "seat_class": random.choice(["economy", "business", "first"]),
        })
    return flights


def generate_hotels(count=1000):
    hotels = []
    for i in range(count):
        city = random.choice(CITIES)
        chain = random.choice(HOTEL_CHAINS)
        hotels.append({
            "hotel_id": f"HT{i+1:04d}",
            "name": f"{chain} {city} {random.choice(['Downtown', 'Airport', 'Central', 'Plaza'])}",
            "chain": chain,
            "city": city,
            "address": fake.address(),
            "rating": Decimal(str(round(random.uniform(2.5, 5.0), 1))),
            "price_per_night": Decimal(str(random.randint(80, 500))),
            "currency": "USD",
            "room_type": random.choice(["Standard", "Deluxe", "Suite", "Family Room"]),
            "max_occupancy": random.randint(2, 6),
            "beds_count": random.randint(1, 3),
            "family_friendly": random.choice([True, False]),
            "kids_club": random.choice([True, False]),
            "pool": random.choice([True, False]),
            "playground": random.choice([True, False]),
            "loyalty_program": f"{chain} Rewards",
            "loyalty_benefits": {
                "member": ["Free WiFi"],
                "gold": ["Free WiFi", "Late Checkout", "Room Upgrade"],
                "platinum": ["Free WiFi", "Late Checkout", "Room Upgrade", "Free Breakfast"],
            },
            "points_earned": random.randint(100, 1000),
            "wifi_free": True,
            "breakfast_included": random.choice([True, False]),
            "parking_available": random.choice([True, False]),
            "gym": random.choice([True, False]),
        })
    return hotels


def generate_restaurants(count=1500):
    cuisines = ["Italian", "French", "Chinese", "Japanese", "Mexican", "Indian", "Thai", "American", "Mediterranean", "Korean"]
    dietary_options = ["Vegetarian", "Vegan", "Gluten-Free", "Halal", "Kosher", "Dairy-Free", "Nut-Free"]
    restaurants = []
    for i in range(count):
        city = random.choice(CITIES)
        cuisine = random.choice(cuisines)
        restaurants.append({
            "restaurant_id": f"RT{i+1:04d}",
            "name": f"{fake.company()} {cuisine} {random.choice(['Bistro', 'Restaurant', 'Cafe', 'Kitchen', 'Grill'])}",
            "city": city,
            "cuisine_type": cuisine,
            "address": fake.address(),
            "rating": Decimal(str(round(random.uniform(3.0, 5.0), 1))),
            "price_range": random.choice(["$", "$$", "$$$", "$$$$"]),
            "average_cost_per_person": Decimal(str(random.randint(15, 150))),
            "currency": "USD",
            "kid_friendly": random.choice([True, False]),
            "kids_menu": random.choice([True, False]),
            "high_chairs": random.choice([True, False]),
            "dietary_restrictions": random.sample(dietary_options, random.randint(1, 4)),
            "outdoor_seating": random.choice([True, False]),
            "reservations_required": random.choice([True, False]),
            "delivery_available": random.choice([True, False]),
            "takeout_available": random.choice([True, False]),
            "wheelchair_accessible": random.choice([True, False]),
            "parking_available": random.choice([True, False]),
            "wifi_available": random.choice([True, False]),
            "live_music": random.choice([True, False]),
            "private_dining": random.choice([True, False]),
            "opening_hours": {
                "monday": "11:00-22:00", "tuesday": "11:00-22:00", "wednesday": "11:00-22:00",
                "thursday": "11:00-22:00", "friday": "11:00-23:00", "saturday": "10:00-23:00",
                "sunday": "10:00-21:00",
            },
            "phone": fake.phone_number(),
            "website": f"https://www.{fake.domain_name()}",
            "reviews_count": random.randint(50, 2000),
        })
    return restaurants


def generate_attractions(count=1000):
    types = ["Museum", "Park", "Monument", "Zoo", "Aquarium", "Theater", "Gallery", "Garden", "Castle", "Beach"]
    attractions = []
    for i in range(count):
        city = random.choice(CITIES)
        atype = random.choice(types)
        attractions.append({
            "attraction_id": f"AT{i+1:04d}",
            "name": f"{city} {atype} {random.choice(['Center', 'Plaza', 'Gardens', 'Hall', 'Complex'])}",
            "city": city,
            "type": atype,
            "category": random.choice(["Cultural", "Entertainment", "Nature", "Historical", "Educational", "Adventure"]),
            "address": fake.address(),
            "rating": Decimal(str(round(random.uniform(3.5, 5.0), 1))),
            "admission_price": Decimal(str(random.randint(0, 50))),
            "currency": "USD",
            "min_age": random.choice([0, 3, 6, 12, 16, 18]),
            "max_age": random.choice([99, 65, 12, 8]) if random.random() > 0.8 else 99,
            "duration_hours": Decimal(str(round(random.uniform(0.5, 8.0), 1))),
            "family_friendly": random.choice([True, False]),
            "kid_friendly": random.choice([True, False]),
            "stroller_friendly": random.choice([True, False]),
            "wheelchair_accessible": random.choice([True, False]),
            "indoor": random.choice([True, False]),
            "outdoor": random.choice([True, False]),
            "weather_dependent": random.choice([True, False]),
            "guided_tours": random.choice([True, False]),
            "audio_guide": random.choice([True, False]),
            "gift_shop": random.choice([True, False]),
            "cafe_restaurant": random.choice([True, False]),
            "parking_available": random.choice([True, False]),
            "public_transport": random.choice([True, False]),
            "photography_allowed": random.choice([True, False]),
            "group_discounts": random.choice([True, False]),
            "opening_hours": {
                "monday": "09:00-17:00", "tuesday": "09:00-17:00", "wednesday": "09:00-17:00",
                "thursday": "09:00-17:00", "friday": "09:00-18:00", "saturday": "09:00-18:00",
                "sunday": "10:00-17:00",
            },
            "seasonal_hours": random.choice([True, False]),
            "phone": fake.phone_number(),
            "website": f"https://www.{fake.domain_name()}",
            "reviews_count": random.randint(100, 5000),
        })
    return attractions


def _weather_activities(condition, temp):
    if condition in ["Sunny", "Partly Cloudy"] and temp > 15:
        return ["Outdoor sightseeing", "Walking tours", "Parks and gardens", "Outdoor dining"]
    if condition in ["Rainy", "Stormy"]:
        return ["Museums", "Indoor attractions", "Shopping malls", "Theaters"]
    if temp < 5:
        return ["Indoor activities", "Hot beverages", "Warm clothing shopping"]
    if temp > 30:
        return ["Swimming", "Air-conditioned venues", "Early morning activities"]
    return ["General sightseeing", "Mixed indoor/outdoor activities"]


def _clothing(condition, temp):
    s = []
    if temp < 0:
        s = ["Heavy coat", "Gloves", "Hat", "Warm boots", "Layers"]
    elif temp < 10:
        s = ["Jacket", "Long pants", "Closed shoes", "Light layers"]
    elif temp < 20:
        s = ["Light jacket", "Comfortable clothing", "Layers"]
    elif temp < 30:
        s = ["Light clothing", "Comfortable shoes", "Sun hat"]
    else:
        s = ["Very light clothing", "Sunscreen", "Hat", "Sunglasses"]
    if condition in ["Rainy", "Stormy"]:
        s += ["Umbrella", "Rain jacket", "Waterproof shoes"]
    return s


def _travel_impact(condition, temp):
    if condition in ["Stormy", "Snowy"]:
        return "High - Possible delays and cancellations"
    if condition == "Rainy":
        return "Medium - Minor delays possible"
    if condition == "Foggy":
        return "Medium - Visibility issues possible"
    return "Low - Normal travel conditions"


def _family_considerations(condition, temp):
    c = []
    if temp < 5:
        c.append("Keep children warm and limit outdoor exposure")
    elif temp > 30:
        c.append("Ensure children stay hydrated and use sunscreen")
    if condition in ["Rainy", "Stormy"]:
        c.append("Plan indoor activities for children")
    elif condition == "Sunny":
        c.append("Great weather for outdoor family activities")
    return c


def generate_weather(count=1000):
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy", "Windy"]
    records = []
    for i in range(count):
        city = random.choice(CITIES)
        cond = random.choice(conditions)
        temp = random.randint(-10, 40)
        records.append({
            "weather_id": f"WE{i+1:04d}",
            "city": city,
            "date": fake.date_between(start_date="+1d", end_date="+365d").isoformat(),
            "condition": cond,
            "temperature": temp,
            "temperature_unit": "C",
            "temperature_fahrenheit": int(temp * 9 / 5 + 32),
            "humidity": random.randint(30, 90),
            "wind_speed": random.randint(0, 30),
            "wind_unit": "km/h",
            "precipitation_chance": random.randint(0, 100),
            "uv_index": random.randint(1, 11),
            "visibility": random.randint(1, 20),
            "air_quality": random.choice(["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy"]),
            "sunrise": f"{random.randint(5,8):02d}:{random.randint(0,59):02d}",
            "sunset": f"{random.randint(17,20):02d}:{random.randint(0,59):02d}",
            "recommended_activities": _weather_activities(cond, temp),
            "clothing_suggestions": _clothing(cond, temp),
            "travel_impact": _travel_impact(cond, temp),
            "family_considerations": _family_considerations(cond, temp),
        })
    return records


def _redemption_options(cat):
    base = ["Statement credit", "Gift cards", "Merchandise"]
    extras = {
        "Airlines": ["Free flights", "Seat upgrades", "Lounge access"],
        "Hotels": ["Free nights", "Room upgrades", "Late checkout"],
        "Restaurants": ["Free meals", "Discounts", "Priority reservations"],
        "Car Rental": ["Free rentals", "Upgrades", "Express service"],
    }
    return base + extras.get(cat, ["Travel credits", "Partner transfers"])


def _tier_benefits(tier):
    base = ["Points earning", "Customer service"]
    if tier == "member":
        return base
    if tier == "silver":
        return base + ["Priority check-in", "25% bonus points"]
    if tier == "gold":
        return base + ["Priority check-in", "50% bonus points", "Free upgrades", "Late checkout"]
    return base + ["Priority everything", "100% bonus points", "Free upgrades", "Concierge service", "Exclusive events"]


def generate_loyalty(count=50):
    categories = ["Airlines", "Hotels", "Restaurants", "Car Rental", "Credit Cards", "Travel Agencies"]
    programs = []
    for i in range(count):
        cat = random.choice(categories)
        programs.append({
            "program_id": f"LP{i+1:04d}",
            "name": f"{fake.company()} {cat[:-1]} Rewards",
            "category": cat,
            "company": fake.company(),
            "description": f"Earn points and enjoy exclusive benefits with {fake.company()}",
            "currency": "points",
            "enrollment_fee": Decimal(str(random.choice([0, 25, 50, 99]))),
            "annual_fee": Decimal(str(random.choice([0, 95, 195, 495]))),
            "earning_rate": {"base": random.randint(1, 5), "bonus_categories": random.randint(2, 10), "partner_bonus": random.randint(1, 3)},
            "redemption_options": _redemption_options(cat),
            "tiers": {
                "member": {"name": "Member", "qualification": "Enrollment", "benefits": _tier_benefits("member")},
                "silver": {"name": "Silver", "qualification": f"{random.randint(10,25)}K points or {random.randint(10,25)} stays/flights", "benefits": _tier_benefits("silver")},
                "gold": {"name": "Gold", "qualification": f"{random.randint(50,75)}K points or {random.randint(25,50)} stays/flights", "benefits": _tier_benefits("gold")},
                "platinum": {"name": "Platinum", "qualification": f"{random.randint(100,150)}K points or {random.randint(75,100)} stays/flights", "benefits": _tier_benefits("platinum")},
            },
            "partner_programs": random.sample(["Marriott", "Hilton", "American Airlines", "Delta", "United", "Hertz", "Avis"], random.randint(2, 4)),
            "expiration_policy": random.choice(["24 months", "18 months", "No expiration", "12 months"]),
            "family_sharing": random.choice([True, False]),
            "transfer_partners": random.choice([True, False]),
            "website": f"https://www.{fake.domain_name()}",
            "customer_service": fake.phone_number(),
            "mobile_app": random.choice([True, False]),
        })
    return programs


def _fake_email():
    first = random.choice(["john", "jane", "michael", "sarah", "david", "emily", "robert", "lisa", "james", "maria"])
    last = random.choice(["smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis"])
    domain = random.choice(["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com"])
    return f"{first}.{last}@{domain}"


def _fake_name():
    return f"{random.choice(['John','Jane','Michael','Sarah','David','Emily','Robert','Lisa','James','Maria'])} {random.choice(['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis'])}"


def _fake_phone():
    return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"


def generate_reservations(count=100):
    destinations = [
        "Paris, France", "Tokyo, Japan", "New York, USA", "London, UK",
        "Rome, Italy", "Barcelona, Spain", "Sydney, Australia", "Dubai, UAE",
        "Bangkok, Thailand", "Amsterdam, Netherlands", "Berlin, Germany",
        "Los Angeles, USA", "Singapore", "Istanbul, Turkey", "Prague, Czech Republic",
        "Vienna, Austria", "Copenhagen, Denmark", "Stockholm, Sweden", "Zurich, Switzerland",
    ]
    statuses = ["confirmed", "pending", "cancelled", "completed"]
    loyalty_programs = ["Marriott Bonvoy", "Hilton Honors", "IHG Rewards", "Hyatt World",
                        "American Airlines AAdvantage", "Delta SkyMiles", "United MileagePlus"]
    dietary = ["vegetarian", "vegan", "gluten_free", "kosher", "halal", "none"]
    reservations = []

    for i in range(count):
        now = datetime.now()
        created = now - timedelta(days=random.randint(0, 180))
        start = now + timedelta(days=random.randint(0, 365))
        nights = random.randint(3, 14)
        end = start + timedelta(days=nights)
        adults = random.randint(1, 4)
        children = random.randint(0, 3)
        flight_cost = Decimal(str(random.randint(400, 2500)))
        hotel_per_night = Decimal(str(random.randint(80, 500)))
        hotel_total = hotel_per_night * nights
        activity_cost = Decimal(str(random.randint(100, 800)))
        subtotal = flight_cost + hotel_total + activity_cost
        taxes = subtotal * Decimal("0.12")
        total = subtotal + taxes

        reservations.append({
            "reservation_id": f"RES{i+1:06d}",
            "user_email": _fake_email(),
            "status": random.choice(statuses),
            "created_date": created.isoformat(),
            "last_modified": now.isoformat(),
            "destination": random.choice(destinations),
            "travel_dates": {"start_date": start.isoformat(), "end_date": end.isoformat(), "duration_days": nights},
            "party_details": {"adults": adults, "children": children, "total_travelers": adults + children},
            "flight_details": {
                "included": random.choice([True, False]),
                "airline": random.choice(AIRLINES),
                "flight_class": random.choice(["economy", "premium_economy", "business", "first"]),
                "cost": flight_cost,
            },
            "accommodation": {
                "hotel_name": f"{random.choice(['Grand','Royal','Imperial','Luxury','Premium','Elite','Golden','Diamond'])} Hotel",
                "room_type": random.choice(["standard", "deluxe", "suite", "family_room"]),
                "nights": nights,
                "cost_per_night": hotel_per_night,
                "total_cost": hotel_total,
            },
            "activities": {"included": random.choice([True, False]), "estimated_count": random.randint(2, 8), "estimated_cost": activity_cost},
            "preferences": {
                "dietary_restrictions": random.sample(dietary, random.randint(0, 2)),
                "budget_level": random.choice(["budget", "mid_range", "luxury"]),
                "loyalty_programs": random.sample(loyalty_programs, random.randint(0, 2)),
            },
            "costs": {"subtotal": subtotal, "taxes_fees": taxes, "total": total, "currency": "USD"},
            "contact_info": {
                "primary_phone": _fake_phone(),
                "emergency_contact": {"name": _fake_name(), "phone": _fake_phone(), "relationship": random.choice(["spouse", "parent", "sibling", "friend"])},
            },
            "special_requests": random.choice([
                None, "Wheelchair accessible rooms", "Late checkout requested",
                "Vegetarian meals only", "Connecting rooms for family",
                "Airport transfer needed", "Celebration - anniversary", "Business traveler - quiet room",
            ]),
            "booking_source": random.choice(["web", "mobile_app", "phone", "travel_agent"]),
            "confirmation_number": f"CONF{random.randint(100000, 999999)}",
        })
    return reservations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🚀 Creating DynamoDB tables...")
    for name, cfg in TABLE_CONFIGS.items():
        create_table(name, cfg)

    print("\n⏳ Waiting for tables to become ACTIVE...")
    wait_for_tables()
    print("✅ All tables ready\n")

    # Generate data
    print("📦 Generating synthetic data...")
    flights = generate_flights(1000)
    hotels = generate_hotels(1000)
    restaurants = generate_restaurants(1500)
    attractions = generate_attractions(1000)
    weather = generate_weather(1000)
    loyalty = generate_loyalty(50)
    reservations = generate_reservations(100)

    # Load subsets to DynamoDB (matching notebook limits)
    print("\n📤 Loading data to DynamoDB...")
    load_items("exec-synthetic-flights", flights[:100])
    load_items("exec-synthetic-hotels", hotels[:100])
    load_items("exec-synthetic-restaurants", restaurants[:150])
    load_items("exec-synthetic-attractions", attractions[:100])
    load_items("exec-synthetic-weather", weather[:100])
    load_items("exec-loyalty-programs", loyalty)
    load_items("exec-travel-reservations", reservations)

    total = 100 + 100 + 150 + 100 + 100 + len(loyalty) + len(reservations)
    print(f"\n🎉 Done! Loaded {total} records across {len(TABLE_CONFIGS)} tables.")


if __name__ == "__main__":
    main()
