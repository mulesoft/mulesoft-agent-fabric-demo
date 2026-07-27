# Copyright 2026 Salesforce.com, Inc.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Policy ───────────────────────────────────────────────────────────────────
POLICY = {
    "max_flight_budget": 1200,
    "max_hotel_per_night": 200,
    "min_days_in_advance": 3,
    "max_total_trip_budget": 3000,
    "cabin_class": "ECONOMY"
}

# ── Lookups ───────────────────────────────────────────────────────────────────
AIRLINE_NAMES = {
    "B6": "JetBlue", "F9": "Frontier", "AA": "American Airlines",
    "DL": "Delta", "UA": "United Airlines", "WN": "Southwest",
    "AS": "Alaska Airlines", "NK": "Spirit", "BA": "British Airways",
    "VS": "Virgin Atlantic", "LH": "Lufthansa", "AF": "Air France",
    "WS": "WestJet"
}

CITY_CODE_ALIASES = {
    "CDG": "PAR", "ORY": "PAR",
    "LHR": "LON", "LGW": "LON", "STN": "LON",
    "JFK": "NYC", "LGA": "NYC", "EWR": "NYC",
    "ORD": "CHI", "MDW": "CHI",
    "OAK": "SFO",
    "HND": "TYO", "NRT": "TYO",
    "LAX": "LAX", "DXB": "DXB", "SFO": "SFO",
    "SIN": "SIN", "SYD": "SYD", "ATL": "ATL", "HKG": "HKG",
}

AGENT_CARD = {
    "name": "travel-planner-agent",
    "displayName": "Travel Planner Agent",
    "description": "Searches flights and hotels for business travel. Validates policy compliance.",
    "version": "1.0.0",
    "url": os.environ.get("AGENT_URL", "https://your-api-gateway-url"),
    "capabilities": {"streaming": False, "pushNotifications": False},
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "skills": [
        {
            "id": "search-travel",
            "name": "Search Travel Options",
            "description": "Search flights and hotels given origin, destination, travel dates and city code",
            "tags": [],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
            "parameters": {
                "type": "object",
                "properties": {
                    "origin":       {"type": "string", "description": "Departure IATA code e.g. ATL"},
                    "destination":  {"type": "string", "description": "Arrival IATA code e.g. LON"},
                    "travel_date":  {"type": "string", "description": "Departure date YYYY-MM-DD"},
                    "check_out":    {"type": "string", "description": "Return date YYYY-MM-DD"},
                    "city_code":    {"type": "string", "description": "Hotel city code e.g. LON"}
                },
                "required": ["origin", "destination", "travel_date", "check_out", "city_code"]
            }
        }
    ]
}

# ── Hotel data (static — zero latency) ───────────────────────────────────────
HOTEL_DATA = {
    "NYC": [
        {"hotel_name": "Marriott Midtown",          "address": "1535 Broadway, New York",             "distance_to_meeting": "0.3 miles", "price_per_night": 189.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Downtown",         "address": "85 West St, New York",                "distance_to_meeting": "0.8 miles", "price_per_night": 175.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Financial Center", "address": "85 Broad St, New York",               "distance_to_meeting": "1.2 miles", "price_per_night": 165.00, "rating": "3 stars"},
    ],
    "LON": [
        {"hotel_name": "Marriott Grosvenor Square", "address": "Grosvenor Square, London",            "distance_to_meeting": "0.3 miles", "price_per_night": 195.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Canary Wharf",     "address": "22 Hertsmere Rd, London",             "distance_to_meeting": "0.6 miles", "price_per_night": 180.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Kensington",       "address": "Cromwell Rd, London",                 "distance_to_meeting": "1.1 miles", "price_per_night": 160.00, "rating": "3 stars"},
    ],
    "PAR": [
        {"hotel_name": "Marriott Champs-Elysees",   "address": "70 Ave des Champs-Elysees, Paris",    "distance_to_meeting": "0.2 miles", "price_per_night": 210.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Rive Gauche",      "address": "17 Blvd St-Jacques, Paris",           "distance_to_meeting": "0.7 miles", "price_per_night": 185.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Opera Ambassador", "address": "16 Blvd Haussmann, Paris",            "distance_to_meeting": "1.0 miles", "price_per_night": 170.00, "rating": "3 stars"},
    ],
    "DXB": [
        {"hotel_name": "Marriott Al Jaddaf",        "address": "Al Jaddaf, Dubai",                    "distance_to_meeting": "0.4 miles", "price_per_night": 175.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Downtown Dubai",   "address": "Sheikh Mohammed Bin Rashid Blvd",     "distance_to_meeting": "0.6 miles", "price_per_night": 195.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Deira",            "address": "Al Muraqqabat, Deira, Dubai",         "distance_to_meeting": "1.3 miles", "price_per_night": 155.00, "rating": "3 stars"},
    ],
    "SIN": [
        {"hotel_name": "Marriott Tang Plaza",       "address": "320 Orchard Rd, Singapore",           "distance_to_meeting": "0.3 miles", "price_per_night": 185.00, "rating": "4 stars"},
        {"hotel_name": "Marriott South Beach",      "address": "30 Beach Rd, Singapore",              "distance_to_meeting": "0.8 miles", "price_per_night": 170.00, "rating": "4 stars"},
        {"hotel_name": "Marriott City Hall",        "address": "5 Coleman St, Singapore",             "distance_to_meeting": "1.1 miles", "price_per_night": 150.00, "rating": "3 stars"},
    ],
    "SYD": [
        {"hotel_name": "Marriott Darling Harbour",  "address": "30 Pyrmont St, Sydney",               "distance_to_meeting": "0.4 miles", "price_per_night": 180.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Circular Quay",    "address": "36 College St, Sydney",               "distance_to_meeting": "0.7 miles", "price_per_night": 195.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Surry Hills",      "address": "4-6 Randle St, Sydney",               "distance_to_meeting": "1.4 miles", "price_per_night": 155.00, "rating": "3 stars"},
    ],
    "LAX": [
        {"hotel_name": "Marriott LAX",              "address": "5855 W Century Blvd, Los Angeles",    "distance_to_meeting": "0.3 miles", "price_per_night": 169.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Downtown LA",      "address": "333 S Figueroa St, Los Angeles",      "distance_to_meeting": "0.9 miles", "price_per_night": 179.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Marina del Rey",   "address": "13480 Maxella Ave, Los Angeles",      "distance_to_meeting": "1.5 miles", "price_per_night": 155.00, "rating": "3 stars"},
    ],
    "CHI": [
        {"hotel_name": "Marriott Magnificent Mile", "address": "540 N Michigan Ave, Chicago",         "distance_to_meeting": "0.2 miles", "price_per_night": 175.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Medical District", "address": "625 S Ashland Ave, Chicago",          "distance_to_meeting": "0.8 miles", "price_per_night": 159.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Midway",           "address": "6520 S Cicero Ave, Chicago",          "distance_to_meeting": "1.3 miles", "price_per_night": 139.00, "rating": "3 stars"},
    ],
    "SFO": [
        {"hotel_name": "Marriott Union Square",     "address": "480 Sutter St, San Francisco",        "distance_to_meeting": "0.2 miles", "price_per_night": 199.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Fishermans Wharf", "address": "1250 Columbus Ave, San Francisco",    "distance_to_meeting": "0.9 miles", "price_per_night": 185.00, "rating": "4 stars"},
        {"hotel_name": "Marriott SFO Airport",      "address": "1800 Old Bayshore Hwy, Burlingame",   "distance_to_meeting": "1.6 miles", "price_per_night": 155.00, "rating": "3 stars"},
    ],
    "HKG": [
        {"hotel_name": "Marriott Pacific Place",    "address": "88 Queensway, Hong Kong",             "distance_to_meeting": "0.3 miles", "price_per_night": 195.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Kowloon",          "address": "3 Observatory Rd, Kowloon",           "distance_to_meeting": "0.7 miles", "price_per_night": 180.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Skycity",          "address": "1 Sky City Rd, Lantau",               "distance_to_meeting": "1.2 miles", "price_per_night": 160.00, "rating": "3 stars"},
    ],
    "TYO": [
        {"hotel_name": "Marriott Tokyo",            "address": "2-10-3 Nagatacho, Tokyo",             "distance_to_meeting": "0.4 miles", "price_per_night": 200.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Shiodome",         "address": "1-9-1 Higashi-Shimbashi, Tokyo",      "distance_to_meeting": "0.8 miles", "price_per_night": 185.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Shinjuku",         "address": "2-7-2 Nishi-Shinjuku, Tokyo",         "distance_to_meeting": "1.3 miles", "price_per_night": 165.00, "rating": "3 stars"},
    ],
    "ATL": [
        {"hotel_name": "Marriott Marquis Atlanta",  "address": "265 Peachtree Center Ave, Atlanta",   "distance_to_meeting": "0.2 miles", "price_per_night": 159.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Buckhead",         "address": "3444 Peachtree Rd, Atlanta",          "distance_to_meeting": "0.6 miles", "price_per_night": 149.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Airport",          "address": "4711 Best Rd, College Park",          "distance_to_meeting": "1.4 miles", "price_per_night": 129.00, "rating": "3 stars"},
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_json_loads(value, default=None):
    if default is None:
        default = {}
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


# ── Flight search via RapidAPI ────────────────────────────────────────────────
def search_flights(origin, destination, outbound_date, return_date=None):
    logger.info("[FLIGHTS] START %s → %s on %s (return: %s)", origin, destination, outbound_date, return_date)
    try:
        host = os.environ["RAPIDAPI_HOST"]
        key  = os.environ["RAPIDAPI_KEY"]
        logger.info("[FLIGHTS] Env vars loaded — host: %s", host)

        params = {
            "departure_id": origin,
            "arrival_id":   destination,
            "outbound_date": outbound_date,
            "travel_class": "ECONOMY",
            "adults": 1,
            "currency": "USD",
            "language_code": "en-US",
            "country_code": "US",
            "search_type": "best"
        }
        if return_date:
            params["return_date"] = return_date

        url = f"https://{host}/api/v1/searchFlights?" + urllib.parse.urlencode(params)
        logger.info("[FLIGHTS] Calling RapidAPI: %s", url)

        req = urllib.request.Request(url)
        req.add_header("x-rapidapi-host", host)
        req.add_header("x-rapidapi-key",  key)

        with urllib.request.urlopen(req, timeout=5) as res:
            raw = res.read().decode("utf-8")
            logger.info("[FLIGHTS] RapidAPI response received — length: %d chars", len(raw))
            data = json.loads(raw)

        itineraries = data.get("data", {}).get("itineraries", {})
        top_flights  = itineraries.get("topFlights", [])
        logger.info("[FLIGHTS] topFlights count: %d", len(top_flights))

        flights = []
        for item in top_flights[:5]:
            legs = item.get("flights", [])
            if not legs:
                continue
            first_leg = legs[0]
            last_leg  = legs[-1]
            dep_ap    = first_leg.get("departure_airport", {})
            arr_ap    = last_leg.get("arrival_airport",   {})
            ac        = first_leg.get("flight_number", "")[:2].upper()
            flight_price = float(item.get("price", 0))
            flights.append({
                "id":               f"{ac}-{dep_ap.get('airport_code', origin)}-{arr_ap.get('airport_code', destination)}",
                "price":            flight_price,
                "currency":         "USD",
                "airline":          ac or first_leg.get("airline", ""),
                "airline_name":     AIRLINE_NAMES.get(ac, first_leg.get("airline", "Unknown")),
                "departure":        dep_ap.get("time"),
                "arrival":          arr_ap.get("time"),
                "departure_airport": dep_ap.get("airport_code", origin),
                "arrival_airport":  arr_ap.get("airport_code", destination),
                "stops":            len(legs) - 1,
                "duration":         item.get("duration", {}).get("text"),
                "within_policy":    flight_price <= POLICY["max_flight_budget"],
                "route":            f"{dep_ap.get('airport_code', origin)} → {arr_ap.get('airport_code', destination)}"
            })

        if flights:
            logger.info("[FLIGHTS] Parsed %d flights OK — cheapest: $%s", len(flights), min(f["price"] for f in flights))
            return flights
        raise ValueError("No flight offers returned")

    except KeyError as e:
        logger.error("[FLIGHTS] Missing env var: %s — falling back to demo data", e)
    except Exception as e:
        logger.error("[FLIGHTS] RapidAPI call failed: %s — falling back to demo data", e)

    logger.warning("[FLIGHTS] Using hardcoded fallback flights for %s → %s", origin, destination)
    return [
        {
            "id": f"DL-{origin}-{destination}",
            "price": 367.0, "currency": "USD",
            "airline": "DL", "airline_name": "Delta",
            "departure": f"{outbound_date}T06:00:00",
            "arrival":   f"{outbound_date}T11:45:00",
            "departure_airport": origin, "arrival_airport": destination,
            "stops": 0, "duration": "5 hr 45 min",
            "within_policy": True,
            "route": f"{origin} → {destination}"
        },
        {
            "id": f"AA-{origin}-{destination}",
            "price": 412.0, "currency": "USD",
            "airline": "AA", "airline_name": "American Airlines",
            "departure": f"{outbound_date}T08:30:00",
            "arrival":   f"{outbound_date}T14:20:00",
            "departure_airport": origin, "arrival_airport": destination,
            "stops": 0, "duration": "5 hr 50 min",
            "within_policy": True,
            "route": f"{origin} → {destination}"
        }
    ]


# ── Hotel lookup (pure dict — zero latency) ───────────────────────────────────
def search_hotels(city_code, check_in, check_out):
    original = city_code
    city_code = CITY_CODE_ALIASES.get(city_code.upper(), city_code.upper())
    if original.upper() != city_code:
        logger.info("[HOTELS] Mapped %s → %s", original, city_code)
    logger.info("[HOTELS] Looking up hotels for city: %s", city_code)
    raw = HOTEL_DATA.get(city_code, [
        {"hotel_name": "Marriott City Center",     "address": f"City Center, {city_code}",     "distance_to_meeting": "0.5 miles", "price_per_night": 169.00, "rating": "4 stars"},
        {"hotel_name": "Marriott Business District","address": f"Business District, {city_code}","distance_to_meeting": "0.9 miles", "price_per_night": 155.00, "rating": "3 stars"},
    ])
    hotels = [
        {**h, "price_per_night": float(h["price_per_night"]), "currency": "USD", "within_policy": h["price_per_night"] <= POLICY["max_hotel_per_night"]}
        for h in raw
    ]
    logger.info("[HOTELS] Returned %d hotels for %s", len(hotels), city_code)
    return hotels


# ── Policy check ──────────────────────────────────────────────────────────────
def check_policy(travel_date, check_out, flights, hotels):
    violations = []
    try:
        travel_dt   = datetime.strptime(travel_date, "%Y-%m-%d").date()
        check_out_dt = datetime.strptime(check_out,  "%Y-%m-%d").date()
        days_ahead  = (travel_dt - date.today()).days
        num_nights  = max((check_out_dt - travel_dt).days, 1)
    except Exception as e:
        return [f"Date parsing failed: {e}"]

    if days_ahead < POLICY["min_days_in_advance"]:
        violations.append(f"Booking {days_ahead} days ahead — policy requires {POLICY['min_days_in_advance']}+")

    cheapest_flight = min(flights, key=lambda x: x.get("price", 10**9)) if flights else None
    cheapest_hotel  = min(hotels,  key=lambda x: x.get("price_per_night", 10**9)) if hotels else None

    fp = cheapest_flight["price"] if cheapest_flight else 0
    hp = cheapest_hotel["price_per_night"] if cheapest_hotel else 0

    if cheapest_flight and not cheapest_flight.get("within_policy"):
        violations.append(f"Cheapest flight ${fp} exceeds max ${POLICY['max_flight_budget']}")
    if cheapest_hotel and not cheapest_hotel.get("within_policy"):
        violations.append(f"Cheapest hotel ${hp}/night exceeds max ${POLICY['max_hotel_per_night']}/night")

    total = fp + hp * num_nights
    if total > POLICY["max_total_trip_budget"]:
        violations.append(f"Total ${total:.2f} exceeds max ${POLICY['max_total_trip_budget']} ({num_nights} nights)")

    return violations


# ── Core search — runs flights + hotels in parallel ───────────────────────────
def build_result(origin, destination, travel_date, check_out, city_code):
    logger.info("[BUILD] Starting parallel search: %s → %s | %s to %s | hotels in %s",
                origin, destination, travel_date, check_out, city_code)
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_future = ex.submit(search_flights, origin, destination, travel_date, check_out)
        h_future = ex.submit(search_hotels, city_code, travel_date, check_out)
        flights = f_future.result()
        hotels  = h_future.result()

    logger.info("[BUILD] Search complete — %d flights, %d hotels", len(flights), len(hotels))
    violations = check_policy(travel_date, check_out, flights, hotels)
    status = "ESCALATE_FOR_APPROVAL" if violations else "READY_TO_BOOK"
    logger.info("[BUILD] Policy check done — status: %s, violations: %d", status, len(violations))

    return {
        "status":           status,
        "policy_violations": violations,
        "flights":          flights,
        "hotels":           hotels,
        "message":          "Policy violations found — escalating for approval" if violations
                            else "All within policy — ready to book!"
    }


# ── Bedrock action group handler ──────────────────────────────────────────────
def handle_bedrock_agent_call(event):
    logger.info("[BEDROCK] Action group invocation received")
    action_group = event.get("actionGroup", "")
    api_path     = event.get("apiPath", "/search")
    properties   = (
        event.get("requestBody", {})
             .get("content", {})
             .get("application/json", {})
             .get("properties", [])
    )

    params = {p.get("name"): p.get("value") for p in properties}
    logger.info("[BEDROCK] Parsed params: %s", params)

    origin      = params.get("origin",      "ATL")
    destination = params.get("destination", "LON")
    travel_date = params.get("travel_date", "2026-07-10")
    check_out   = params.get("check_out",   "2026-07-12")
    city_code   = params.get("city_code",   "LON")

    logger.info("[BEDROCK] %s → %s | %s to %s | city: %s", origin, destination, travel_date, check_out, city_code)
    result = build_result(origin, destination, travel_date, check_out, city_code)
    logger.info("[BEDROCK] Result ready — status: %s", result.get("status"))

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup":   action_group,
            "apiPath":       api_path,
            "httpMethod":    "POST",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }


# ── A2A JSON-RPC handler ──────────────────────────────────────────────────────
def handle_a2a_message(a2a_body):
    message_id = a2a_body.get("id", "unknown")
    logger.info("[A2A] JSON-RPC message received — id: %s", message_id)
    params     = a2a_body.get("params", {})
    parts      = params.get("message", {}).get("parts", [])
    logger.info("[A2A] Message parts count: %d", len(parts))

    travel_params = {}
    for part in parts:
        if part.get("kind") == "data":
            travel_params = part.get("data", {})
            logger.info("[A2A] Extracted data part: %s", travel_params)
        elif part.get("kind") == "text":
            text = part.get("text", "")
            # Try JSON first
            parsed = safe_json_loads(text, {})
            if parsed and isinstance(parsed, dict):
                travel_params = parsed
                logger.info("[A2A] Extracted text part (parsed JSON): %s", travel_params)
            else:
                # Parse plain text "key: value\n" format sent by AgentFabric LLM
                for line in text.splitlines():
                    if ":" in line:
                        key, _, val = line.partition(":")
                        key = key.strip().lower().replace(" ", "_")
                        val = val.strip()
                        if key in ("origin", "destination", "travel_date", "check_out", "city_code") and val:
                            travel_params[key] = val
                if travel_params:
                    logger.info("[A2A] Extracted text part (plain text parse): %s", travel_params)

    origin      = travel_params.get("origin",      "ATL")
    destination = travel_params.get("destination", "LON")
    travel_date = travel_params.get("travel_date", "2026-07-10")
    check_out   = travel_params.get("check_out",   "2026-07-12")
    city_code   = travel_params.get("city_code",   "LON")

    logger.info("[A2A] %s → %s | %s to %s | city: %s", origin, destination, travel_date, check_out, city_code)
    result = build_result(origin, destination, travel_date, check_out, city_code)
    logger.info("[A2A] Result ready — status: %s", result.get("status"))

    task_id = message_id

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "kind": "task",
                "id": task_id,
                "contextId": message_id,
                "status": {
                    "state": "completed",
                    "timestamp": "2026-01-01T00:00:00Z"
                },
                "artifacts": [
                    {
                        "artifactId": "travel-options-1",
                        "name": "travel-options",
                        "parts": [{"kind": "data", "data": result}]
                    }
                ],
                "history": [],
                "metadata": {}
            }
        })
    }


# ── Main handler ──────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    try:
        logger.info("[HANDLER] Invocation start — remaining ms: %d", context.get_remaining_time_in_millis())
        logger.info("[HANDLER] Event keys: %s", list(event.keys()))

        # 1. Bedrock action group invocation
        if "actionGroup" in event:
            logger.info("[HANDLER] Route → Bedrock action group")
            return handle_bedrock_agent_call(event)

        # 2. Detect HTTP method + path from API Gateway v2 (HTTP API) payload
        http_ctx    = event.get("requestContext", {}).get("http", {})
        http_method = (http_ctx.get("method") or event.get("httpMethod", "POST")).upper()
        path        = http_ctx.get("path") or event.get("path", "/")
        logger.info("[HANDLER] HTTP %s %s", http_method, path)

        # 3. Agent Card
        if http_method == "GET" and ".well-known" in path:
            logger.info("[HANDLER] Route → Agent Card")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(AGENT_CARD)
            }

        # 4. Parse body
        body_raw = event.get("body")
        body = safe_json_loads(body_raw) if body_raw else event
        logger.info("[HANDLER] Body keys: %s", list(body.keys()) if isinstance(body, dict) else "non-dict")

        # 5. A2A JSON-RPC
        if "jsonrpc" in body:
            logger.info("[HANDLER] Route → A2A JSON-RPC")
            return handle_a2a_message(body)

        # 6. Direct REST search
        logger.info("[HANDLER] Route → Direct REST search")
        origin      = body.get("origin",      "ATL")
        destination = body.get("destination", "JFK")
        travel_date = body.get("travel_date", "2026-07-10")
        check_out   = body.get("check_out",   "2026-07-12")
        city_code   = body.get("city_code",   "NYC")

        result = build_result(origin, destination, travel_date, check_out, city_code)
        logger.info("[HANDLER] Done — returning 200")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, indent=2)
        }

    except Exception as e:
        logger.exception("[HANDLER] Unhandled error: %s", e)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
