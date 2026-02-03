"""
MongoDB Connector.

Syncs collections and documents from a MongoDB database using pymongo.

Docs: https://pymongo.readthedocs.io/
"""
import logging
from typing import Any, Dict, Iterator, List, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

from backend.connectors.sdk.base import (
    BaseConnector,
    ConnectorCapabilities,
    ConnectorMetadata,
    AuthType,
    PaginationType,
)
from backend.connectors.sdk.registry import register_connector

logger = logging.getLogger(__name__)


def _serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB-specific types to JSON-serializable Python types."""
    serialized = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, dict):
            serialized[key] = _serialize_document(value)
        elif isinstance(value, list):
            serialized[key] = [
                _serialize_document(item) if isinstance(item, dict)
                else str(item) if isinstance(item, ObjectId)
                else item
                for item in value
            ]
        else:
            serialized[key] = value
    return serialized


@register_connector
class MongoDBConnector(BaseConnector):
    """MongoDB database connector."""

    metadata = ConnectorMetadata(
        name="mongodb",
        display_name="MongoDB",
        description="Sync collections and documents from a MongoDB database.",
        icon="mongodb",
        category="database",
        capabilities=ConnectorCapabilities(
            supports_incremental=False,
            supports_schema_discovery=True,
            auth_types=[AuthType.BASIC],
            pagination_type=PaginationType.NONE,
        ),
    )

    def setup(self):
        self.connection_string = self.config.require("connection_string")
        self.database_name = self.config.require("database")
        self.collections_filter: Optional[List[str]] = self.config.get("collections")
        self._client: Optional[MongoClient] = None

    def _get_client(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=10_000,
            )
        return self._client

    def _get_db(self):
        return self._get_client()[self.database_name]

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["connection_string", "database"],
            "properties": {
                "connection_string": {
                    "type": "string",
                    "description": "MongoDB connection string (e.g. mongodb+srv://user:pass@cluster.mongodb.net)",
                    "secret": True,
                },
                "database": {
                    "type": "string",
                    "description": "Database name to connect to",
                },
                "collections": {
                    "type": "array",
                    "description": "Optional list of collections to sync. If empty, all collections are synced.",
                    "items": {"type": "string"},
                },
            },
        }

    def test_connection(self) -> Dict[str, Any]:
        try:
            db = self._get_db()
            collection_names = db.list_collection_names()
            return {
                "success": True,
                "message": f"Connected. Found {len(collection_names)} collection(s).",
            }
        except (ConnectionFailure, OperationFailure) as e:
            return {"success": False, "message": str(e)}

    def discover_schema(self) -> List[Dict[str, Any]]:
        db = self._get_db()
        collection_names = db.list_collection_names()

        if self.collections_filter:
            collection_names = [
                c for c in collection_names if c in self.collections_filter
            ]

        schema = []
        for name in sorted(collection_names):
            # Sample one document to infer column types
            sample = db[name].find_one()
            columns = []
            if sample:
                for field_name, value in sample.items():
                    col_type = "string"
                    if isinstance(value, bool):
                        col_type = "boolean"
                    elif isinstance(value, int):
                        col_type = "integer"
                    elif isinstance(value, float):
                        col_type = "number"
                    elif isinstance(value, dict):
                        col_type = "object"
                    elif isinstance(value, list):
                        col_type = "array"
                    elif isinstance(value, ObjectId):
                        col_type = "string"

                    columns.append({
                        "name": field_name,
                        "type": col_type,
                        "primary_key": field_name == "_id",
                    })

            schema.append({
                "name": name,
                "description": f"MongoDB collection: {name}",
                "columns": columns,
                "supports_incremental": False,
            })

        return schema

    def extract(
        self,
        table_name: Optional[str] = None,
        collection: Optional[str] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """
        Extract documents from a MongoDB collection.

        Args:
            table_name: Name of the collection to extract from.
            collection: Alias for table_name.

        Yields:
            Serialized document dicts with ObjectIds converted to strings.
        """
        target = collection or table_name
        if not target:
            raise ValueError(
                "A collection name is required. Pass table_name or collection."
            )

        db = self._get_db()

        if target not in db.list_collection_names():
            raise ValueError(
                f"Collection '{target}' not found in database '{self.database_name}'."
            )

        logger.info(f"Extracting MongoDB collection: {target}")
        cursor = db[target].find()

        for doc in cursor:
            yield _serialize_document(doc)

    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None
