import time
from pathlib import Path

import requests

LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
DOWNLOAD_URL = "https://www.ercot.com/misdownload/servlets/mirDownload"
HEADERS = {"User-Agent": "gis-queue-feed (personal learning project)"}
RAW_DIR = Path("data/raw")


def get_with_retries(url, params, timeout, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            if attempt == attempts:
                raise
            wait = 5 * attempt
            print(f"Attempt {attempt} failed ({error}); retrying in {wait}s")
            time.sleep(wait)


def list_documents():
    response = get_with_retries(LIST_URL, {"reportTypeId": 15933}, timeout=30)
    data = response.json()
    entries = data["ListDocsByRptTypeRes"]["DocumentList"]
    return [entry["Document"] for entry in entries]


def keep_gis_reports(documents):
    return [doc for doc in documents if doc["FriendlyName"].startswith("GIS_Report")]


def download(doc):
    filename = f"{doc['PublishDate'][:10]}_{doc['DocID']}_{doc['FriendlyName']}.{doc['Extension']}"
    path = RAW_DIR / filename

    if path.exists():
        print("Already downloaded, skipping:", filename)
        return path

    response = get_with_retries(DOWNLOAD_URL, {"doclookupId": doc["DocID"]}, timeout=60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print("Downloaded:", filename)
    time.sleep(2)
    return path


if __name__ == "__main__":
    gis_reports = keep_gis_reports(list_documents())
    print(len(gis_reports), "GIS reports available")

    for doc in gis_reports:
        try:
            download(doc)
        except requests.RequestException as error:
            print(f"FAILED {doc['FriendlyName']}: {error}")
