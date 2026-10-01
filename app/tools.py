import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
import requests
import inspect

load_dotenv()

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-f62308c10678"
MEDIA_BUCKET_NAME = "apartment-agent-media-qwiklabs-gcp-03-f62308c10678"


def _get_db() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def list_apartments(
    max_price: int | None = None,
    min_bedrooms: int | None = None,
    neighborhood: str | None = None,
) -> list[dict]:
    """Search and filter available apartment listings from Firestore.

    Args:
        max_price: Optional maximum monthly rent price.
        min_bedrooms: Optional minimum number of bedrooms.
        neighborhood: Optional neighborhood name to filter by (case-insensitive substring).

    Returns:
        List of matching apartment listings with details.
    """
    db = _get_db()
    docs = db.collection("apartments").stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if max_price is not None and data.get("price", 0) > max_price:
            continue
        if min_bedrooms is not None and data.get("bedrooms", 0) < min_bedrooms:
            continue
        if neighborhood and neighborhood.lower() not in data.get("neighborhood", "").lower():
            continue
        results.append(data)
    return results


def get_apartment_details(apartment_id: str) -> dict | str:
    """Retrieve detailed information for a specific apartment by its ID.

    Args:
        apartment_id: Unique identifier for the apartment (e.g., 'apt-101').

    Returns:
        Dictionary containing apartment details, or error message if not found.
    """
    db = _get_db()
    doc_ref = db.collection("apartments").document(apartment_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Apartment with ID '{apartment_id}' not found."
    return doc.to_dict()


def add_apartment_listing(
    title: str,
    neighborhood: str,
    price: int,
    bedrooms: int,
    bathrooms: float = 1.0,
    pets_allowed: bool = False,
    description: str = "",
    amenities: list[str] | None = None,
) -> dict:
    """Add a new apartment listing to Firestore.

    Args:
        title: Title of the apartment listing.
        neighborhood: Neighborhood location.
        price: Monthly rent price in USD.
        bedrooms: Number of bedrooms.
        bathrooms: Number of bathrooms.
        pets_allowed: Whether pets are allowed.
        description: Description of the property.
        amenities: List of amenity tags (e.g., ['in-unit laundry', 'balcony']).

    Returns:
        Dictionary confirming the newly created apartment listing.
    """
    db = _get_db()
    coll_ref = db.collection("apartments")
    docs = list(coll_ref.stream())
    apt_id = f"apt-{len(docs) + 101}"
    listing = {
        "id": apt_id,
        "title": title,
        "neighborhood": neighborhood,
        "price": price,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "pets_allowed": pets_allowed,
        "amenities": amenities or [],
        "description": description,
        "available": True,
    }
    coll_ref.document(apt_id).set(listing)
    return listing


def schedule_apartment_viewing(
    apartment_id: str,
    preferred_date: str,
    contact_name: str,
    contact_email: str,
) -> dict | str:
    """Schedule a tour or viewing for a specific apartment listing.

    Args:
        apartment_id: Unique ID of the apartment (e.g., 'apt-101').
        preferred_date: Preferred date and time for the viewing (e.g., '2026-10-05 at 2:00 PM').
        contact_name: Full name of the person requesting the viewing.
        contact_email: Email address for the viewing confirmation.

    Returns:
        Dictionary confirming the scheduled viewing record and confirmation ID.
    """
    db = _get_db()
    apt_doc = db.collection("apartments").document(apartment_id).get()
    if not apt_doc.exists:
        return f"Cannot schedule viewing: Apartment ID '{apartment_id}' does not exist."

    apt_data = apt_doc.to_dict()
    coll_ref = db.collection("viewings")
    viewing_docs = list(coll_ref.stream())
    confirmation_id = f"viewing-{len(viewing_docs) + 1001}"

    record = {
        "confirmation_id": confirmation_id,
        "apartment_id": apartment_id,
        "apartment_title": apt_data.get("title", ""),
        "preferred_date": preferred_date,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "status": "Confirmed",
    }
    coll_ref.document(confirmation_id).set(record)
    return record


def get_location_by_zipcode(zip_code: str) -> dict | str:
    """Lookup city, state, latitude, and longitude for a US ZIP code using the Zippopotam.us public API.

    Args:
        zip_code: 5-digit US ZIP code (e.g., '94103', '10001', '02116').

    Returns:
        Dictionary containing location details (city, state, coordinates) or error message.
    """
    clean_zip = str(zip_code).strip()
    api_key = os.getenv("ZIPPOPOTAMUS_API_KEY", "")  # Optional API key override if needed
    url = f"https://api.zippopotam.us/us/{clean_zip}"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 404:
            return f"ZIP code '{zip_code}' not found."
        response.raise_for_status()
        data = response.json()
        places = data.get("places", [])
        if not places:
            return f"No location details found for ZIP code '{zip_code}'."
        place = places[0]
        return {
            "zip_code": data.get("post code"),
            "city": place.get("place name"),
            "state": place.get("state"),
            "state_code": place.get("state abbreviation"),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
        }
    except Exception as exc:
        return f"Error looking up ZIP code '{zip_code}': {exc}"


def geocode_address(address: str) -> dict | str:
    """Convert a street address into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: Street address or location description (e.g., '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address, latitude, and longitude, or error string.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return "Error: GOOGLE_MAPS_API_KEY is not configured in environment variables."

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK" or not data.get("results"):
            return f"Geocoding failed for address '{address}': status {data.get('status', 'NO_RESULTS')}"

        result = data["results"][0]
        location = result.get("geometry", {}).get("location", {})
        return {
            "formatted_address": result.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
        }
    except Exception as exc:
        return f"Error calling Geocoding API: {exc}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
) -> list[dict] | str:
    """Find nearby points of interest (restaurants, cafes, parks, etc.) near given coordinates using Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g., 'restaurant', 'cafe', 'park', 'supermarket').
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        List of dictionaries with place name, formatted address, location coordinates, and place types.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return "Error: GOOGLE_MAPS_API_KEY is not configured in environment variables."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }
    body = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        raw_places = data.get("places", [])

        results = []
        for p in raw_places:
            results.append({
                "name": p.get("displayName", {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "location": p.get("location", {}),
                "types": p.get("types", []),
            })
        return results
    except Exception as exc:
        return f"Error calling Places API (New): {exc}"


def generate_apartment_image(
    prompt: str,
    apartment_id: str | None = None,
    tool_context: ToolContext | None = None,
) -> dict | str:
    """Generate a realistic interior or exterior preview image for an apartment listing using Gemini 3.1 Flash Lite Image.

    Args:
        prompt: Detailed description of the apartment interior, room, view, or property exterior to visualize.
        apartment_id: Optional identifier for the apartment (e.g., 'apt-101').
        tool_context: ADK context automatically provided to save artifacts.

    Returns:
        Dictionary containing the public Cloud Storage HTTPS URL of the generated image and status.
    """
    client = genai.Client(
        vertexai=True,
        location="global",
        project=FIRESTORE_PROJECT_ID,
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                    image_size="1K",
                ),
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return "Failed to generate image: No image data returned from model."

        ext = "png" if "png" in mime_type else "jpg"
        filename = f"{apartment_id or 'apartment_preview'}.{ext}"

        # (1) Save artifact with tool_context.save_artifact so it shows in Playground Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload in-memory image bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(MEDIA_BUCKET_NAME)
        object_name = f"previews/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{MEDIA_BUCKET_NAME}/{object_name}"
        return {
            "apartment_id": apartment_id,
            "prompt": prompt,
            "public_image_url": public_url,
            "message": "Generated image successfully saved as artifact and uploaded to public Cloud Storage bucket.",
        }
    except Exception as exc:
        return f"Error generating apartment image: {exc}"


async def generate_apartment_tour_video(
    prompt: str,
    tool_context: ToolContext | None = None,
    apartment_id: str | None = None,
) -> dict | str:
    """Generate a short video walkthrough preview for an apartment listing using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        prompt: Description of the apartment interior or video walkthrough (e.g. 'Short walkthrough of a luxury 2-bedroom living room with floor to ceiling windows').
        tool_context: ADK ToolContext used to record the artifact.
        apartment_id: Optional ID of the apartment listing.

    Returns:
        Dict containing public Cloud Storage video URL and status.
    """
    try:
        import base64
        import time
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)

        url = f"https://aiplatform.googleapis.com/v1beta1/projects/{FIRESTORE_PROJECT_ID}/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gemini-omni-flash-preview",
            "input": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            "response_format": [
                {
                    "type": "video",
                    "resolution": "720p",
                    "duration": "5s",
                    "aspect_ratio": "16:9",
                }
            ],
            "generation_config": {
                "video_config": {
                    "task": "text_to_video"
                }
            },
        }

        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            return f"Failed to generate video: HTTP {resp.status_code} - {resp.text}"

        resp_json = resp.json()
        b64_data = None
        mime_type = "video/mp4"

        # Check steps -> content -> data
        steps = resp_json.get("steps", [])
        for step in steps:
            for content in step.get("content", []):
                if content.get("type") == "video" and content.get("data"):
                    b64_data = content.get("data")
                    mime_type = content.get("mime_type", "video/mp4")
                    break
            if b64_data:
                break

        # Fallback check for outputs
        if not b64_data:
            outputs = resp_json.get("outputs", [])
            for out in outputs:
                for part in out.get("parts", []):
                    if part.get("type") == "video" and part.get("data"):
                        b64_data = part.get("data")
                        mime_type = part.get("mime_type", "video/mp4")
                        break

        if not b64_data:
            return "Failed to generate video: No video data returned in response."

        video_bytes = base64.b64decode(b64_data)
        timestamp = int(time.time())
        filename = f"video_{apartment_id or timestamp}.mp4"

        # (1) Save artifact with tool_context.save_artifact so it shows in Playground Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            res = tool_context.save_artifact(filename=filename, artifact=artifact_part)
            if inspect.isawaitable(res):
                await res

        # (2) Upload in-memory video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(MEDIA_BUCKET_NAME)
        object_name = f"videos/{filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{MEDIA_BUCKET_NAME}/{object_name}"
        return {
            "apartment_id": apartment_id,
            "prompt": prompt,
            "public_video_url": public_url,
            "message": "Generated video successfully saved as artifact and uploaded to public Cloud Storage bucket.",
        }
    except Exception as exc:
        return f"Error generating apartment video: {exc}"






