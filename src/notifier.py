import httpx

NTFY_URL = "https://ntfy.sh"
DEFAULT_TOPIC = "Iq69p41S2golYAOG-rove"


def send_notification(
    message: str,
    *,
    title: str = "Rove Miles Daily Monitor",
    topic: str = DEFAULT_TOPIC,
    priority: str = "default",
    tags: list[str] | None = None,
) -> None:
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "markdown": True,
        "priority": _priority_int(priority),
    }
    if tags:
        payload["tags"] = tags

    response = httpx.post(
        NTFY_URL,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()


def _priority_int(priority: str) -> int:
    return {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}.get(priority, 3)


if __name__ == "__main__":
    send_notification("Test notification from Rove Monitor", tags=["test", "white_check_mark"])
    print("Notification sent!")
