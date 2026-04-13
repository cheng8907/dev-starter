import os

import httpx
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    host = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
    chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY") or None
    funder = os.getenv("POLYMARKET_FUNDER") or None

    mode = "authenticated-ready" if private_key else "read-only"

    with httpx.Client(base_url=host, timeout=10.0) as client:
        ok_response = client.get("/ok")
        time_response = client.get("/time")

    print(f"Polymarket client mode: {mode}")
    print(f"Host: {host}")
    print(f"Chain ID: {chain_id}")
    print(f"Funder configured: {bool(funder)}")
    print(f"API healthy: {ok_response.json()}")
    print(f"Server time: {time_response.json()}")


if __name__ == "__main__":
    main()
