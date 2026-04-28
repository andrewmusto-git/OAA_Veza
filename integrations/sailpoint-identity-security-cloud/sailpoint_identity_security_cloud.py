#!/usr/bin/env python3
"""
SailPoint Identity Security Cloud to Veza OAA Integration Script
Collects identity and permission data from SailPoint Identity Security Cloud and pushes to Veza.
"""
import argparse
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from oaaclient.client import OAAClient, OAAClientError
from oaaclient.templates import CustomApplication, OAAPermission


logger = logging.getLogger(__name__)


class SailPointClient:
    """SailPoint Identity Security Cloud API client."""

    def __init__(self, tenant_url: str, client_id: str, client_secret: str):
        """
        Initialize SailPoint client.
        
        Args:
            tenant_url: SailPoint tenant URL (e.g., https://acme.identitynow.com)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.tenant_url = tenant_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        self._authenticate()

    def _authenticate(self) -> None:
        """Obtain access token using client credentials flow."""
        auth_url = urljoin(self.tenant_url, "/oauth/token")
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in - 60
            logger.info("Successfully authenticated with SailPoint API")
        except requests.RequestException as e:
            logger.error("Failed to authenticate with SailPoint: %s", e)
            sys.exit(1)

    def _ensure_valid_token(self) -> None:
        """Re-authenticate if token is expired."""
        if time.time() >= self.token_expires_at:
            logger.debug("Access token expired, re-authenticating...")
            self._authenticate()

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None
    ) -> Dict:
        """
        Make API request with token management.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to tenant URL)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
        """
        self._ensure_valid_token()
        url = urljoin(self.tenant_url, endpoint)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(
                method, url, headers=headers, params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("API request failed (%s %s): %s", method, endpoint, e)
            raise

    def get_paginated_results(
        self, endpoint: str, limit: int = 250
    ) -> List[Dict]:
        """
        Fetch all results from paginated endpoint.
        
        Args:
            endpoint: API endpoint
            limit: Items per page (SailPoint max: 250)
            
        Returns:
            List of all items across pages
        """
        results = []
        offset = 0
        while True:
            params = {"limit": limit, "offset": offset}
            try:
                data = self._make_request("GET", endpoint, params=params)
                items = data if isinstance(data, list) else data.get("items", [])
                if not items:
                    break
                results.extend(items)
                offset += limit
            except requests.RequestException:
                logger.warning(
                    "Pagination stopped at offset %d; returning partial results",
                    offset,
                )
                break
        return results

    def get_roles(self) -> List[Dict]:
        """Fetch all roles."""
        logger.info("Fetching roles from SailPoint...")
        return self.get_paginated_results("/beta/roles")

    def get_access_profiles(self) -> List[Dict]:
        """Fetch all access profiles."""
        logger.info("Fetching access profiles from SailPoint...")
        return self.get_paginated_results("/beta/access-profiles")

    def get_entitlements(self) -> List[Dict]:
        """Fetch all entitlements."""
        logger.info("Fetching entitlements from SailPoint...")
        return self.get_paginated_results("/beta/entitlements")

    def get_sources(self) -> List[Dict]:
        """Fetch all sources."""
        logger.info("Fetching sources from SailPoint...")
        return self.get_paginated_results("/v3/sources")

    def get_identities(self) -> List[Dict]:
        """Fetch all identities (users)."""
        logger.info("Fetching identities from SailPoint...")
        return self.get_paginated_results("/v3/identities")

    def get_identity_access_profiles(self, identity_id: str) -> List[Dict]:
        """Fetch access profiles assigned to an identity."""
        try:
            endpoint = f"/v3/identities/{identity_id}/access-profiles"
            return self._make_request("GET", endpoint)
        except requests.RequestException:
            logger.debug("Failed to fetch access profiles for identity %s", identity_id)
            return []

    def get_identity_entitlements(self, identity_id: str) -> List[Dict]:
        """Fetch entitlements assigned to an identity."""
        try:
            endpoint = f"/beta/identities/{identity_id}/entitlements"
            return self._make_request("GET", endpoint)
        except requests.RequestException:
            logger.debug("Failed to fetch entitlements for identity %s", identity_id)
            return []


def build_oaa_payload(sailpoint_data: Dict) -> CustomApplication:
    """
    Build OAA CustomApplication from SailPoint data.
    
    Args:
        sailpoint_data: Dictionary containing identities, roles, access_profiles, etc.
        
    Returns:
        CustomApplication object with all entities and permissions
    """
    app = CustomApplication(
        name="SailPoint Identity Security Cloud",
        application_type="SailPoint Identity Security Cloud"
    )

    # Define permission sets for read-only access
    app.add_custom_permission(
        "read",
        [OAAPermission.DataRead]
    )
    app.add_custom_permission(
        "write",
        [OAAPermission.DataRead, OAAPermission.DataWrite]
    )
    app.add_custom_permission(
        "admin",
        [OAAPermission.DataRead, OAAPermission.DataWrite, OAAPermission.MetadataRead, OAAPermission.MetadataWrite]
    )

    # Track unique sources and roles
    sources_map = {}
    roles_map = {}
    entitlements_map = {}

    # Add sources as resources
    logger.info("Processing sources...")
    for source in sailpoint_data.get("sources", []):
        source_id = source.get("id")
        source_name = source.get("name", f"Source-{source_id}")
        source_type = source.get("type", "Unknown")
        
        app.add_resource(
            resource_id=source_id,
            resource_name=source_name,
            resource_type=source_type,
            details={"description": source.get("description", "")}
        )
        sources_map[source_id] = source_name
        logger.debug("Added source: %s (%s)", source_name, source_id)

    # Add roles as resources
    logger.info("Processing roles...")
    for role in sailpoint_data.get("roles", []):
        role_id = role.get("id")
        role_name = role.get("name", f"Role-{role_id}")
        
        app.add_resource(
            resource_id=role_id,
            resource_name=role_name,
            resource_type="Role",
            details={"description": role.get("description", "")}
        )
        roles_map[role_id] = role_name
        logger.debug("Added role: %s (%s)", role_name, role_id)

    # Add access profiles as resources
    logger.info("Processing access profiles...")
    for ap in sailpoint_data.get("access_profiles", []):
        ap_id = ap.get("id")
        ap_name = ap.get("name", f"AccessProfile-{ap_id}")
        
        app.add_resource(
            resource_id=ap_id,
            resource_name=ap_name,
            resource_type="AccessProfile",
            details={"description": ap.get("description", "")}
        )
        logger.debug("Added access profile: %s (%s)", ap_name, ap_id)

    # Add entitlements as resources
    logger.info("Processing entitlements...")
    for entitlement in sailpoint_data.get("entitlements", []):
        ent_id = entitlement.get("id")
        ent_name = entitlement.get("name", f"Entitlement-{ent_id}")
        source_id = entitlement.get("source", {}).get("id") if isinstance(entitlement.get("source"), dict) else entitlement.get("source")
        
        app.add_resource(
            resource_id=ent_id,
            resource_name=ent_name,
            resource_type="Entitlement",
            details={
                "description": entitlement.get("description", ""),
                "source": sources_map.get(source_id, source_id)
            }
        )
        entitlements_map[ent_id] = ent_name
        logger.debug("Added entitlement: %s (%s)", ent_name, ent_id)

    # Add users and their access
    logger.info("Processing identities and their access assignments...")
    for identity in sailpoint_data.get("identities", []):
        identity_id = identity.get("id")
        identity_name = identity.get("name", identity_id)
        email = identity.get("email", "")
        
        user_attrs = {
            "email": email,
            "status": identity.get("status", "Active"),
        }
        
        app.add_local_user(
            user_id=identity_id,
            user_name=identity_name,
            user_email=email,
            user_attributes=user_attrs
        )
        logger.debug("Added user: %s (%s)", identity_name, identity_id)

        # Add role memberships
        roles = identity.get("roles", [])
        for role in roles:
            role_id = role.get("id") if isinstance(role, dict) else role
            role_name = roles_map.get(role_id, f"Role-{role_id}")
            
            try:
                app.add_assignment(
                    user_id=identity_id,
                    resource_id=role_id,
                    permissions=["read"]
                )
                logger.debug("Assigned role %s to user %s", role_name, identity_name)
            except Exception as e:
                logger.warning("Failed to assign role %s to user %s: %s", role_name, identity_name, e)

        # Add access profile assignments
        access_profiles = identity.get("access_profiles", [])
        for ap in access_profiles:
            ap_id = ap.get("id") if isinstance(ap, dict) else ap
            ap_name = ap.get("name", f"AccessProfile-{ap_id}") if isinstance(ap, dict) else f"AccessProfile-{ap_id}"
            
            try:
                app.add_assignment(
                    user_id=identity_id,
                    resource_id=ap_id,
                    permissions=["read"]
                )
                logger.debug("Assigned access profile %s to user %s", ap_name, identity_name)
            except Exception as e:
                logger.warning("Failed to assign access profile %s to user %s: %s", ap_name, identity_name, e)

        # Add entitlement assignments
        entitlements = identity.get("entitlements", [])
        for ent in entitlements:
            ent_id = ent.get("id") if isinstance(ent, dict) else ent
            ent_name = entitlements_map.get(ent_id, f"Entitlement-{ent_id}")
            
            try:
                app.add_assignment(
                    user_id=identity_id,
                    resource_id=ent_id,
                    permissions=["read"]
                )
                logger.debug("Assigned entitlement %s to user %s", ent_name, identity_name)
            except Exception as e:
                logger.warning("Failed to assign entitlement %s to user %s: %s", ent_name, identity_name, e)

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
        description="SailPoint Identity Security Cloud to Veza OAA Integration"
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
        default="SailPoint Identity Security Cloud",
        help="Provider name in Veza (default: SailPoint Identity Security Cloud)",
    )
    parser.add_argument(
        "--datasource-name",
        default=None,
        help="Data source name in Veza (default: SailPoint instance name)",
    )
    
    # SailPoint arguments
    parser.add_argument(
        "--sailpoint-tenant-url",
        default=os.getenv("SAILPOINT_TENANT_URL"),
        required=True,
        help="SailPoint tenant URL (env: SAILPOINT_TENANT_URL)",
    )
    parser.add_argument(
        "--sailpoint-client-id",
        default=os.getenv("SAILPOINT_CLIENT_ID"),
        required=True,
        help="SailPoint OAuth2 client ID (env: SAILPOINT_CLIENT_ID)",
    )
    parser.add_argument(
        "--sailpoint-client-secret",
        default=os.getenv("SAILPOINT_CLIENT_SECRET"),
        required=True,
        help="SailPoint OAuth2 client secret (env: SAILPOINT_CLIENT_SECRET)",
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
    
    if not args.sailpoint_tenant_url or not args.sailpoint_client_id or not args.sailpoint_client_secret:
        logger.error("SailPoint credentials are required")
        sys.exit(1)
    
    # Set default datasource name if not provided
    if not args.datasource_name:
        args.datasource_name = args.sailpoint_tenant_url.split(".")[0].title()
    
    # Print startup banner
    print("=" * 70)
    print("SailPoint Identity Security Cloud → Veza OAA Integration")
    print("=" * 70)
    print(f"Veza URL: {args.veza_url}")
    print(f"SailPoint Tenant: {args.sailpoint_tenant_url}")
    print(f"Provider Name: {args.provider_name}")
    print(f"Data Source Name: {args.datasource_name}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    print()
    
    try:
        # Connect to SailPoint
        logger.info("Connecting to SailPoint...")
        sailpoint = SailPointClient(
            args.sailpoint_tenant_url,
            args.sailpoint_client_id,
            args.sailpoint_client_secret,
        )
        
        # Fetch data from SailPoint
        sailpoint_data = {
            "identities": sailpoint.get_identities(),
            "roles": sailpoint.get_roles(),
            "access_profiles": sailpoint.get_access_profiles(),
            "entitlements": sailpoint.get_entitlements(),
            "sources": sailpoint.get_sources(),
        }
        
        logger.info(
            "Fetched %d identities, %d roles, %d access profiles, %d entitlements, %d sources",
            len(sailpoint_data["identities"]),
            len(sailpoint_data["roles"]),
            len(sailpoint_data["access_profiles"]),
            len(sailpoint_data["entitlements"]),
            len(sailpoint_data["sources"]),
        )
        
        # Build OAA payload
        logger.info("Building OAA payload...")
        app = build_oaa_payload(sailpoint_data)
        
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
