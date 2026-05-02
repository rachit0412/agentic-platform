"""
Drive Connectors — Google Drive and SharePoint.

Pull documents from cloud document management systems.
"""

import logging
import json
import io
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Google Drive ───────────────────────────────────────────────────────────

def pull_google_drive(config: dict) -> list[dict]:
    """
    Pull documents from a Google Drive folder using service account credentials.
    Returns list of {"name": str, "content": str, "metadata": dict}
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        raise ImportError("google-api-python-client not installed. Run: pip install google-api-python-client google-auth")

    creds_json = json.loads(config["credentials_json"])
    folder_id = config["folder_id"]
    file_types = [t.strip() for t in config.get("file_types", "").split(",") if t.strip()]

    credentials = service_account.Credentials.from_service_account_info(
        creds_json, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=credentials)

    # Build query
    query = f"'{folder_id}' in parents and trashed = false"
    mime_filter = _build_mime_filter(file_types)
    if mime_filter:
        query += f" and ({mime_filter})"

    documents = []
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
            pageSize=100,
        ).execute()

        for file in results.get("files", []):
            content = _download_drive_file(service, file)
            if content:
                documents.append({
                    "name": file["name"],
                    "content": content,
                    "metadata": {"source": f"gdrive://{file['id']}", "mime_type": file["mimeType"]},
                })

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"Google Drive connector pulled {len(documents)} documents from folder {folder_id}")
    return documents


def test_google_drive(config: dict) -> dict:
    """Test Google Drive connectivity."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_json = json.loads(config["credentials_json"])
        credentials = service_account.Credentials.from_service_account_info(
            creds_json, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        service = build("drive", "v3", credentials=credentials)
        folder = service.files().get(fileId=config["folder_id"], fields="name").execute()
        return {"ok": True, "message": f"Connected to folder: {folder['name']}"}
    except ImportError as e:
        return {"ok": False, "message": f"Missing dependency: {e}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _download_drive_file(service, file: dict) -> Optional[str]:
    """Download file content as text."""
    mime = file["mimeType"]
    file_id = file["id"]

    # Google Docs → export as plain text
    if mime == "application/vnd.google-apps.document":
        response = service.files().export(fileId=file_id, mimeType="text/plain").execute()
        return response.decode("utf-8", errors="replace") if isinstance(response, bytes) else str(response)

    # Google Sheets → export as CSV
    if mime == "application/vnd.google-apps.spreadsheet":
        response = service.files().export(fileId=file_id, mimeType="text/csv").execute()
        return response.decode("utf-8", errors="replace") if isinstance(response, bytes) else str(response)

    # Binary files → download
    if mime.startswith("text/") or mime in ("application/pdf", "application/json"):
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue().decode("utf-8", errors="replace")

    return None


def _build_mime_filter(file_types: list) -> str:
    """Build MIME type filter for Google Drive query."""
    mime_map = {
        "document": "mimeType = 'application/vnd.google-apps.document'",
        "spreadsheet": "mimeType = 'application/vnd.google-apps.spreadsheet'",
        "pdf": "mimeType = 'application/pdf'",
        "text": "mimeType = 'text/plain'",
    }
    parts = [mime_map[t] for t in file_types if t in mime_map]
    return " or ".join(parts) if parts else ""


# ─── SharePoint ─────────────────────────────────────────────────────────────

def pull_sharepoint(config: dict) -> list[dict]:
    """
    Pull documents from a SharePoint document library.
    Returns list of {"name": str, "content": str, "metadata": dict}
    """
    try:
        import msal
        import requests
    except ImportError:
        raise ImportError("msal not installed. Run: pip install msal requests")

    site_url = config["site_url"]
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    tenant_id = config["tenant_id"]
    library = config.get("library", "Shared Documents")

    token = _get_sharepoint_token(tenant_id, client_id, client_secret)
    site_id = _get_site_id(token, site_url)
    drive_id = _get_drive_id(token, site_id, library)

    documents = []
    items = _list_drive_items(token, drive_id)

    for item in items:
        if "file" not in item:
            continue
        content = _download_sharepoint_file(token, drive_id, item["id"])
        if content:
            documents.append({
                "name": item["name"],
                "content": content,
                "metadata": {"source": f"sharepoint://{site_url}/{item['name']}", "size": item.get("size", 0)},
            })

    logger.info(f"SharePoint connector pulled {len(documents)} documents from {site_url}")
    return documents


def test_sharepoint(config: dict) -> dict:
    """Test SharePoint connectivity."""
    try:
        import msal
        token = _get_sharepoint_token(config["tenant_id"], config["client_id"], config["client_secret"])
        if token:
            return {"ok": True, "message": f"Authenticated to tenant {config['tenant_id']}"}
        return {"ok": False, "message": "Failed to acquire token"}
    except ImportError as e:
        return {"ok": False, "message": f"Missing dependency: {e}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _get_sharepoint_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Acquire OAuth token for Microsoft Graph."""
    import msal
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    raise Exception(f"Token acquisition failed: {result.get('error_description', 'Unknown error')}")


def _get_site_id(token: str, site_url: str) -> str:
    """Get SharePoint site ID from Graph API."""
    import requests
    from urllib.parse import urlparse
    parsed = urlparse(site_url)
    hostname = parsed.hostname
    site_path = parsed.path.rstrip("/")
    url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["id"]


def _get_drive_id(token: str, site_id: str, library_name: str) -> str:
    """Get drive ID for a document library."""
    import requests
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    for drive in r.json().get("value", []):
        if drive["name"] == library_name:
            return drive["id"]
    raise ValueError(f"Library '{library_name}' not found")


def _list_drive_items(token: str, drive_id: str) -> list[dict]:
    """List all items in the root of a drive."""
    import requests
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("value", [])


def _download_sharepoint_file(token: str, drive_id: str, item_id: str) -> Optional[str]:
    """Download file content from SharePoint."""
    import requests
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.content.decode("utf-8", errors="replace")
    return None
