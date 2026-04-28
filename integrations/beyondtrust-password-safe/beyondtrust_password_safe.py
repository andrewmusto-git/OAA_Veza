#!/usr/bin/env python3
"""
BeyondTrust Password Safe to Veza OAA Integration Script
Collects identity and permission data from BeyondTrust and pushes to Veza.
"""
import argparse
import csv
import io
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from oaaclient.client import OAAClient, OAAClientError
from oaaclient.templates import CustomApplication, OAAPermission


logger = logging.getLogger(__name__)


class BeyondTrustClient:
    """BeyondTrust Password Safe API client."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        verify_ssl: bool = True,
    ):
        """
        Initialize BeyondTrust client.
        
        Args:
            base_url: BeyondTrust API base URL (e.g., https://api.beyondtrustcloud.com)
            api_key: API key for authentication
            api_secret: API secret for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Version": "1.0",
            "Accept": "application/json",
        })
        self._test_connection()

    def _test_connection(self) -> None:
        """Test connection to BeyondTrust API."""
        try:
            response = self.session.get(
                urljoin(self.base_url, "/api/v1/managed_accounts"),
                auth=(self.api_key, self.api_secret),
                verify=self.verify_ssl,
                timeout=10,
                params={"limit": 1}
            )
            response.raise_for_status()
            logger.info("Successfully authenticated with BeyondTrust API")
        except requests.RequestException as e:
            logger.error("Failed to authenticate with BeyondTrust: %s", e)
            sys.exit(1)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Make API request with authentication.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            JSON response as dictionary
        """
        url = urljoin(self.base_url, endpoint)
        try:
            response = self.session.request(
                method,
                url,
                auth=(self.api_key, self.api_secret),
                params=params,
                json=json_data,
                verify=self.verify_ssl,
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.RequestException as e:
            logger.error("API request failed (%s %s): %s", method, endpoint, e)
            raise

    def _get_paginated_results(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """
        Fetch all results from paginated endpoint.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            limit: Items per page
            
        Returns:
            List of all items across pages
        """
        results = []
        offset = 0
        if params is None:
            params = {}

        while True:
            page_params = {**params, "limit": limit, "offset": offset}
            try:
                data = self._make_request("GET", endpoint, params=page_params)
                items = data if isinstance(data, list) else data.get("items", [])
                
                if not items:
                    break
                
                results.extend(items)
                
                # If we got fewer items than limit, we've reached the end
                if len(items) < limit:
                    break
                
                offset += limit
            except requests.RequestException:
                logger.warning(
                    "Pagination stopped at offset %d; returning partial results",
                    offset,
                )
                break

        return results

    def get_managed_accounts(self) -> List[Dict]:
        """Fetch all managed accounts."""
        logger.info("Fetching managed accounts from BeyondTrust...")
        return self._get_paginated_results("/api/v1/managed_accounts")

    def get_managed_computers(self) -> List[Dict]:
        """Fetch all managed computers."""
        logger.info("Fetching managed computers from BeyondTrust...")
        return self._get_paginated_results("/api/v1/managed_computers")

    def get_managed_account_details(self, account_id: str) -> Dict:
        """Fetch details for a specific managed account."""
        try:
            return self._make_request("GET", f"/api/v1/managed_accounts/{account_id}")
        except requests.RequestException:
            logger.debug("Failed to fetch details for account %s", account_id)
            return {}

    def get_managed_computer_details(self, computer_id: str) -> Dict:
        """Fetch details for a specific managed computer."""
        try:
            return self._make_request("GET", f"/api/v1/managed_computers/{computer_id}")
        except requests.RequestException:
            logger.debug("Failed to fetch details for computer %s", computer_id)
            return {}


def parse_csv_computers(csv_content: str) -> List[Dict]:
    """
    Parse BeyondTrust managed computers from CSV export.
    
    Args:
        csv_content: CSV content as string
        
    Returns:
        List of computer dictionaries
    """
    computers = []
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            if row and any(row.values()):  # Skip empty rows
                computers.append(row)
        logger.info("Parsed %d computers from CSV", len(computers))
    except Exception as e:
        logger.error("Failed to parse CSV: %s", e)
    
    return computers


def build_oaa_payload(beyondtrust_data: Dict) -> CustomApplication:
    """
    Build OAA CustomApplication from BeyondTrust data.
    
    Args:
        beyondtrust_data: Dictionary containing accounts, computers data
        
    Returns:
        CustomApplication object with all entities and permissions
    """
    app = CustomApplication(
        name="BeyondTrust Password Safe",
        application_type="BeyondTrust Password Safe"
    )

    # Define permission sets for read-only access
    app.add_custom_permission(
        "read",
        [OAAPermission.DataRead]
    )
    app.add_custom_permission(
        "view",
        [OAAPermission.DataRead, OAAPermission.MetadataRead]
    )

    computers_map = {}
    accounts_map = {}

    # Add computers as resources
    logger.info("Processing managed computers...")
    for computer in beyondtrust_data.get("computers", []):
        computer_id = computer.get("Id") or computer.get("id")
        computer_name = computer.get("Name") or computer.get("name", f"Computer-{computer_id}")
        status = computer.get("Status") or computer.get("status", "Unknown")
        os_type = computer.get("OS") or computer.get("os", "Unknown")
        
        app.add_resource(
            resource_id=computer_id,
            resource_name=computer_name,
            resource_type="ManagedComputer",
            details={
                "status": status,
                "os": os_type,
                "domain": computer.get("Domain") or computer.get("domain", ""),
                "group_name": computer.get("Group Name") or computer.get("group_name", ""),
                "last_connected": computer.get("Last Connected") or computer.get("last_connected", ""),
                "assigned_policy": computer.get("Assigned Policy") or computer.get("assigned_policy", ""),
            }
        )
        computers_map[computer_id] = computer_name
        logger.debug("Added computer: %s (%s)", computer_name, computer_id)

    # Add managed accounts as resources
    logger.info("Processing managed accounts...")
    for account in beyondtrust_data.get("accounts", []):
        account_id = account.get("Id") or account.get("id")
        account_name = account.get("Account Name") or account.get("account_name", f"Account-{account_id}")
        
        app.add_resource(
            resource_id=account_id,
            resource_name=account_name,
            resource_type="ManagedAccount",
            details={
                "system": account.get("System") or account.get("system", ""),
                "host": account.get("Host") or account.get("host", ""),
                "domain": account.get("Domain") or account.get("domain", ""),
                "description": account.get("Description") or account.get("description", ""),
            }
        )
        accounts_map[account_id] = account_name
        logger.debug("Added account: %s (%s)", account_name, account_id)

    # Add managed computers and accounts as local resources for read access
    # In a typical deployment, these represent the inventoried assets
    logger.info("Creating asset resources...")
    
    # Create a virtual "IT Operations" group with read access to all assets
    app.add_local_group(
        group_id="it-operations",
        group_name="IT Operations - BeyondTrust Read Access"
    )

    # Assign read permissions to all computers
    for computer_id in computers_map.keys():
        try:
            app.add_assignment(
                group_id="it-operations",
                resource_id=computer_id,
                permissions=["read"]
            )
        except Exception as e:
            logger.warning("Failed to assign read permission to computer %s: %s", computer_id, e)

    # Assign read permissions to all accounts
    for account_id in accounts_map.keys():
        try:
            app.add_assignment(
                group_id="it-operations",
                resource_id=account_id,
                permissions=["read"]
            )
        except Exception as e:
            logger.warning("Failed to assign read permission to account %s: %s", account_id, e)

    logger.info("OAA payload built successfully")
    return app


def push_to_veza(
    veza_url: str,
    veza_api_key: str,
    provider_name: str,
    datasource_name: str,
    app: CustomApplication,
    dry_run: bool = False,
) -> None:
    """
    Push OAA payload to Veza.
    
    Args:
        veza_url: Veza instance URL
        veza_api_key: Veza API key
        provider_name: Provider name in Veza
        datasource_name: Data source name in Veza
        app: CustomApplication object
        dry_run: Skip actual push if True
    """
    if dry_run:
        logger.info("[DRY RUN] Payload built successfully — skipping push to Veza")
        return

    try:
        veza_con = OAAClient(url=veza_url, token=veza_api_key)
        logger.info("Pushing data to Veza (%s)...", veza_url)
        
        response = veza_con.push_application(
            provider_name=provider_name,
            data_source_name=datasource_name,
            application_object=app,
        )
        
        if response.get("warnings"):
            for warning in response["warnings"]:
                logger.warning("Veza warning: %s", warning)
        
        logger.info("Successfully pushed to Veza")
    except OAAClientError as e:
        logger.error("Veza push failed: %s — %s (HTTP %s)", e.error, e.message, e.status_code)
        if hasattr(e, "details"):
            for detail in e.details:
                logger.error("  Detail: %s", detail)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BeyondTrust Password Safe to Veza OAA Integration"
    )
    
    # Veza arguments
    parser.add_argument(
        "--veza-url",
        default=os.getenv("VEZA_URL"),
        help="Veza instance URL (env: VEZA_URL)",
    )
    parser.add_argument(
        "--veza-api-key",
        default=os.getenv("VEZA_API_KEY"),
        help="Veza API key (env: VEZA_API_KEY)",
    )
    parser.add_argument(
        "--provider-name",
        default="BeyondTrust Password Safe",
        help="Provider name in Veza (default: BeyondTrust Password Safe)",
    )
    parser.add_argument(
        "--datasource-name",
        default=None,
        help="Data source name in Veza (default: BeyondTrust instance name)",
    )
    
    # BeyondTrust arguments
    parser.add_argument(
        "--beyondtrust-api-url",
        default=os.getenv("BEYONDTRUST_API_URL"),
        required=True,
        help="BeyondTrust API base URL (env: BEYONDTRUST_API_URL)",
    )
    parser.add_argument(
        "--beyondtrust-api-key",
        default=os.getenv("BEYONDTRUST_API_KEY"),
        required=True,
        help="BeyondTrust API key (env: BEYONDTRUST_API_KEY)",
    )
    parser.add_argument(
        "--beyondtrust-api-secret",
        default=os.getenv("BEYONDTRUST_API_SECRET"),
        required=True,
        help="BeyondTrust API secret (env: BEYONDTRUST_API_SECRET)",
    )
    
    # Data source arguments
    parser.add_argument(
        "--csv-computers-file",
        default=None,
        help="Path to CSV file with managed computers (alternative to API)",
    )
    parser.add_argument(
        "--skip-ssl-verify",
        action="store_true",
        help="Skip SSL certificate verification (not recommended for production)",
    )
    
    # General arguments
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build payload but skip push to Veza",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Load .env if it exists
    if args.env_file and os.path.exists(args.env_file):
        load_dotenv(args.env_file)
        logger.info("Loaded environment from %s", args.env_file)
    
    # Validate required arguments
    if not args.veza_url or not args.veza_api_key:
        logger.error("Veza URL and API key are required")
        sys.exit(1)
    
    if not args.beyondtrust_api_url or not args.beyondtrust_api_key or not args.beyondtrust_api_secret:
        logger.error("BeyondTrust API credentials are required")
        sys.exit(1)
    
    # Set default datasource name if not provided
    if not args.datasource_name:
        # Extract instance name from API URL
        args.datasource_name = args.beyondtrust_api_url.split("//")[-1].split(".")[0].title()
    
    # Print startup banner
    print("=" * 70)
    print("BeyondTrust Password Safe → Veza OAA Integration")
    print("=" * 70)
    print(f"Veza URL: {args.veza_url}")
    print(f"BeyondTrust API: {args.beyondtrust_api_url}")
    print(f"Provider Name: {args.provider_name}")
    print(f"Data Source Name: {args.datasource_name}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    print()
    
    try:
        beyondtrust_data = {
            "computers": [],
            "accounts": [],
        }
        
        # Fetch from CSV if provided, otherwise fetch from API
        if args.csv_computers_file:
            logger.info("Loading managed computers from CSV: %s", args.csv_computers_file)
            if not os.path.exists(args.csv_computers_file):
                logger.error("CSV file not found: %s", args.csv_computers_file)
                sys.exit(1)
            
            with open(args.csv_computers_file, "r", encoding="utf-8") as f:
                csv_content = f.read()
                beyondtrust_data["computers"] = parse_csv_computers(csv_content)
        else:
            # Connect to BeyondTrust API
            logger.info("Connecting to BeyondTrust API...")
            beyondtrust = BeyondTrustClient(
                base_url=args.beyondtrust_api_url,
                api_key=args.beyondtrust_api_key,
                api_secret=args.beyondtrust_api_secret,
                verify_ssl=not args.skip_ssl_verify,
            )
            
            # Fetch data from BeyondTrust
            beyondtrust_data["computers"] = beyondtrust.get_managed_computers()
            beyondtrust_data["accounts"] = beyondtrust.get_managed_accounts()
        
        logger.info(
            "Fetched %d computers and %d managed accounts",
            len(beyondtrust_data["computers"]),
            len(beyondtrust_data["accounts"]),
        )
        
        # Build OAA payload
        logger.info("Building OAA payload...")
        app = build_oaa_payload(beyondtrust_data)
        
        # Push to Veza
        push_to_veza(
            args.veza_url,
            args.veza_api_key,
            args.provider_name,
            args.datasource_name,
            app,
            dry_run=args.dry_run,
        )
        
        logger.info("Integration completed successfully")
        
    except Exception as e:
        logger.error("Integration failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
