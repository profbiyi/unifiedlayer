"""
Connectors package.
"""
from backend.connectors.mpesa import mpesa_source, MPesaConnector
from backend.connectors.postgres import postgres_source, PostgreSQLConnector
from backend.connectors.mysql import mysql_source, MySQLConnector
from backend.connectors.whatsapp_business import whatsapp_business_source, WhatsAppBusinessConnector
from backend.connectors.rest_api import rest_api_source, RESTAPIConnector
from backend.connectors.paystack import paystack_source, PaystackConnector
from backend.connectors.stripe_connector import stripe_source, StripeConnector, StripeSDKConnector
from backend.connectors.google_sheets import google_sheets_source, GoogleSheetsConnector

# UK-specific connectors (registered via @register_connector decorator)
from backend.connectors.gocardless import GoCardlessConnector
from backend.connectors.xero import XeroConnector
from backend.connectors.open_banking import OpenBankingConnector
from backend.connectors.hmrc_mtd import HMRCMTDConnector
from backend.connectors.flutterwave import FlutterwaveConnector
from backend.connectors.mtn_momo import MTNMoMoConnector
from backend.connectors.mono import MonoConnector
from backend.connectors.mongodb import MongoDBConnector

# File connectors (registered via @register_connector decorator)
from backend.connectors.csv_connector import CSVConnector
from backend.connectors.local_file import LocalFileConnector, local_files_source

# Generic / open connectors
from backend.connectors.http_file_connector import HttpFileConnector, create_http_file_source
from backend.connectors.rest_api_declarative import RestApiDeclarativeConnector, create_rest_api_source

__all__ = [
    "mpesa_source",
    "MPesaConnector",
    "postgres_source",
    "PostgreSQLConnector",
    "mysql_source",
    "MySQLConnector",
    "whatsapp_business_source",
    "WhatsAppBusinessConnector",
    "rest_api_source",
    "RESTAPIConnector",
    "paystack_source",
    "PaystackConnector",
    "stripe_source",
    "StripeConnector",
    "StripeSDKConnector",
    "google_sheets_source",
    "GoogleSheetsConnector",
    "GoCardlessConnector",
    "XeroConnector",
    "OpenBankingConnector",
    "HMRCMTDConnector",
    "FlutterwaveConnector",
    "MTNMoMoConnector",
    "MonoConnector",
    "MongoDBConnector",
    "CSVConnector",
    "LocalFileConnector",
    "local_files_source",
    "HttpFileConnector",
    "create_http_file_source",
    "RestApiDeclarativeConnector",
    "create_rest_api_source",
]
