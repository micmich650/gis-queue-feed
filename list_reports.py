import requests
from pathlib import Path

LIST_URL = "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
HEADERS = {"User-Agent": "gis-queue-feed (personal learning project)"}


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


documents = list_documents()
print(len(documents), "documents")

for doc in documents[:15]:
    print(doc["PublishDate"][:10], doc["DocID"], doc["FriendlyName"])


DOWNLOAD_URL = "https://www.ercot.com/misdownload/servlets/mirDownload"
RAW_DIR = Path("data/raw")


def keep_gis_reports(documents):
    return [doc for doc in documents if doc["FriendlyName"].startswith("GIS_Report")]


def download(doc):
    response = requests.get(
        DOWNLOAD_URL,
        params={"doclookupId": doc["DocID"]},
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{doc['PublishDate'][:10]}_{doc['DocID']}_{doc['FriendlyName']}.xlsx"
    path = RAW_DIR / filename
    path.write_bytes(response.content)
    return path


gis_reports = keep_gis_reports(documents)
print(len(gis_reports), "GIS reports")

latest = gis_reports[0]
saved_to = download(latest)
print("Saved:", saved_to)