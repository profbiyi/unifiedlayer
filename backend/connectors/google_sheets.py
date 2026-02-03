"""
Google Sheets Connector using dlt framework.

Reads data from Google Spreadsheets via the Google Sheets API v4
with service account authentication.
"""
import json
from typing import Iterator, Dict, Any, Optional, List
from datetime import datetime
import dlt
from dlt.sources import DltResource
from dlt.common.typing import TDataItem
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsAPIError(Exception):
    """Custom exception for Google Sheets API errors."""
    pass


class GoogleSheetsConnector:
    """
    Google Sheets connector using service account authentication.

    Features:
    - Service account JSON auth
    - Multi-sheet support
    - Header row as column keys
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(self, credentials_json: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = self._build_service(credentials_json)

    def _build_service(self, credentials_json: str):
        """Build the Google Sheets API service."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            if isinstance(credentials_json, str):
                creds_dict = json.loads(credentials_json)
            else:
                creds_dict = credentials_json

            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.SCOPES
            )
            return build("sheets", "v4", credentials=credentials)
        except ImportError:
            raise GoogleSheetsAPIError(
                "google-api-python-client and google-auth packages are required. "
                "Install with: pip install google-api-python-client google-auth"
            )
        except Exception as e:
            raise GoogleSheetsAPIError(f"Failed to authenticate: {str(e)}")

    def list_sheets(self) -> List[str]:
        """List all sheet names in the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return [
                sheet["properties"]["title"]
                for sheet in spreadsheet.get("sheets", [])
            ]
        except Exception as e:
            raise GoogleSheetsAPIError(f"Failed to list sheets: {str(e)}")

    def get_sheet_data(self, sheet_name: str) -> Iterator[Dict[str, Any]]:
        """
        Read all data from a sheet, using the first row as headers.

        Yields dicts with header names as keys.
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name,
            ).execute()

            rows = result.get("values", [])
            if len(rows) < 2:
                logger.info(f"Sheet '{sheet_name}' has no data rows")
                return

            headers = rows[0]
            for row in rows[1:]:
                record = {}
                for i, header in enumerate(headers):
                    record[header] = row[i] if i < len(row) else None
                record["_sheet_name"] = sheet_name
                record["_dlt_load_time"] = datetime.now().isoformat()
                yield record

        except Exception as e:
            raise GoogleSheetsAPIError(f"Failed to read sheet '{sheet_name}': {str(e)}")


@dlt.source(name="google_sheets")
def google_sheets_source(
    credentials_json: str = dlt.secrets.value,
    spreadsheet_id: str = dlt.config.value,
    sheets: Optional[List[str]] = None,
) -> List[DltResource]:
    """
    dlt source for Google Sheets data.

    If sheets is None, reads all sheets in the spreadsheet.
    """
    connector = GoogleSheetsConnector(
        credentials_json=credentials_json,
        spreadsheet_id=spreadsheet_id,
    )

    # Determine which sheets to load
    if not sheets:
        sheets = connector.list_sheets()

    logger.info(f"Loading {len(sheets)} sheets from spreadsheet {spreadsheet_id}")

    resources = []
    for sheet_name in sheets:
        @dlt.resource(
            name=sheet_name.lower().replace(" ", "_"),
            write_disposition="replace",
            parallelized=True,
        )
        def sheet_data(sn=sheet_name) -> Iterator[TDataItem]:
            yield from connector.get_sheet_data(sn)

        resources.append(sheet_data)

    logger.info(f"Created {len(resources)} resources for Google Sheets extraction")
    return resources
