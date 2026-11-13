import time
from pathlib import Path

import requests

LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
DOWNLOAD_URL = "https://www.ercot.com/misdownload/servlets/mirDownload"
HEADERS = {"User-Agent": "gis-queue-feed (personal learning project)"}
RAW_DIR = Path("data/raw")


def list_documents():
    response = requests.get(
        LIST_URL,
        params={"reportTypeId": 15933},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    entries = data["ListDocsByRptTypeRes"]["DocumentList"]
    return [entry["Document"] for entry in entries]


def keep_gis_reports(documents):
    return [doc for doc in documents if doc["FriendlyName"].startswith("GIS_Report")]


def download(doc):
    filename = f"{doc['PublishDate'][:10]}_{doc['DocID']}_{doc['FriendlyName']}.xlsx"
    path = RAW_DIR / filename

    if path.exists():
        print("Already downloaded, skipping:", filename)
        return path

    response = requests.get(
        DOWNLOAD_URL,
        params={"doclookupId": doc["DocID"]},
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print("Downloaded:", filename)
    time.sleep(2)
    return path


if __name__ == "__main__":
    gis_reports = keep_gis_reports(list_documents())
    print(len(gis_reports), "GIS reports available")

    for doc in gis_reports[:3]:
        download(doc)