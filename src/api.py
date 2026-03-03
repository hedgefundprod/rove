import httpx

ROVE_API_URL = "https://apps-backend-prod-669635507142.us-central1.run.app/api/v1/shopping/group"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.rovemiles.com",
    "referer": "https://www.rovemiles.com/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}


def fetch_shopping_data() -> dict:
    response = httpx.get(ROVE_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()
    assert payload["success"], f"API returned success=false: {payload}"
    return payload["data"]


if __name__ == "__main__":
    from rich import print as rprint

    data = fetch_shopping_data()
    rprint(f"Categories: {list(data.keys())}")
    total = sum(len(stores) for stores in data.values())
    rprint(f"Total stores: {total}")
