"""Seed script for Firestore apartments collection."""
from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-f62308c10678"

SEED_APARTMENTS = [
    {
        "id": "apt-101",
        "title": "Sunlit Modern Loft in Downtown",
        "neighborhood": "Downtown",
        "price": 2800,
        "bedrooms": 1,
        "bathrooms": 1.0,
        "pets_allowed": True,
        "amenities": ["in-unit laundry", "balcony", "gym", "high-speed internet"],
        "description": "Spacious open-concept loft with floor-to-ceiling windows and updated kitchen appliances.",
        "available": True,
    },
    {
        "id": "apt-102",
        "title": "Charming 2BR Brownstone",
        "neighborhood": "Mission District",
        "price": 3400,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "pets_allowed": False,
        "amenities": ["hardwood floors", "dishwasher", "storage space"],
        "description": "Historic charm meets modern finishes. Quiet street near public transit and popular dining.",
        "available": True,
    },
    {
        "id": "apt-103",
        "title": "Cozy 1BR Harbor View Apartment",
        "neighborhood": "Brooklyn Heights",
        "price": 2400,
        "bedrooms": 1,
        "bathrooms": 1.0,
        "pets_allowed": True,
        "amenities": ["water views", "doorman", "elevator", "in-unit laundry"],
        "description": "Beautiful 1-bedroom with sweeping skyline and water views, steps from the park promenade.",
        "available": True,
    },
    {
        "id": "apt-104",
        "title": "Luxury 3BR Family Penthouse",
        "neighborhood": "Back Bay",
        "price": 4200,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "pets_allowed": True,
        "amenities": ["private roof deck", "garage parking", "fireplace", "central AC"],
        "description": "Top-floor penthouse with private outdoor roof deck and dedicated indoor garage parking.",
        "available": True,
    },
]


def seed_firestore():
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("apartments")
    for apt in SEED_APARTMENTS:
        doc_ref = collection_ref.document(apt["id"])
        doc_ref.set(apt)
        print(f"Seeded document: {apt['id']} ({apt['title']})")
    print("Seeding complete.")


if __name__ == "__main__":
    seed_firestore()
