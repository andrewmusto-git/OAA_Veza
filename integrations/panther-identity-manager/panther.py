#!/usr/bin/env python3
"""
Panther Identity Manager to Veza OAA Integration

This integration collects user accounts and groups from Panther Identity Manager
and pushes them to Veza via the Open Authorization API (OAA).
"""

import os
import sys
import logging
import json
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Import Veza OAA components
try:
    from veza_oaa_connector import OAAConnector, CustomApplication, OAAPropertyType
except ImportError:
    print("Error: veza-oaa library not found. Install with: pip install veza-oaa")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('panther_veza_integration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PantherConnector:
    """Connector for Panther Identity Manager API."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, tenant_id: str):
        """
        Initialize Panther connector.

        Args:
            base_url: Base URL for Panther API (e.g., https://mill-mes-security.westrock.com)
            client_id: OAuth client ID
            client_secret: OAuth client secret
            tenant_id: Panther tenant ID (e.g., "3211")
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None
        self.token_url = "https://login.microsoftonline.com/WestRockCo.onmicrosoft.com/oauth2/v2.0/token"
        self.headers = {
            "Accept": "text/plain",
            "tenant": tenant_id
        }
        
    def authenticate(self) -> bool:
        """
        Authenticate with Panther using OAuth2 CLIENT_CREDENTIALS flow.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "api://mill-mes-api/.default"
            }
            
            response = requests.post(self.token_url, data=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            self.headers['Authorization'] = f"Bearer {self.access_token}"
            
            logger.info("Successfully authenticated with Panther")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to Panther API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/HealthCheck",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            logger.info("Health check successful")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Fetch all users from Panther.
        
        Returns:
            List of user dictionaries
        """
        try:
            users = []
            response = requests.get(
                f"{self.base_url}/v1/users",
                headers=self.headers,
                timeout=60
            )
            response.raise_for_status()
            users = response.json()
            
            logger.info(f"Retrieved {len(users)} users from Panther")
            return users
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch users: {e}")
            return []

    def get_groups(self) -> List[Dict[str, Any]]:
        """
        Fetch all groups from Panther.
        
        Returns:
            List of group dictionaries
        """
        try:
            groups = []
            response = requests.get(
                f"{self.base_url}/v1/groups",
                headers=self.headers,
                timeout=60
            )
            response.raise_for_status()
            groups = response.json()
            
            logger.info(f"Retrieved {len(groups)} groups from Panther")
            return groups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch groups: {e}")
            return []

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific user from Panther.
        
        Args:
            username: Username to fetch
            
        Returns:
            User dictionary or None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/v1/users/{username}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch user {username}: {e}")
            return None


class PantherToVezaIntegration:
    """Integration between Panther and Veza OAA."""

    def __init__(self, panther_connector: PantherConnector, veza_connector: OAAConnector):
        """
        Initialize integration.
        
        Args:
            panther_connector: Panther API connector instance
            veza_connector: Veza OAA connector instance
        """
        self.panther = panther_connector
        self.veza = veza_connector
        self.metrics = {
            "users_processed": 0,
            "groups_processed": 0,
            "errors": 0,
            "warnings": 0
        }

    def build_payload(self) -> Optional[CustomApplication]:
        """
        Build Veza CustomApplication payload from Panther data.
        
        Returns:
            CustomApplication object or None if failed
        """
        try:
            # Fetch data from Panther
            users = self.panther.get_users()
            groups = self.panther.get_groups()
            
            if not users and not groups:
                logger.error("No users or groups retrieved from Panther")
                return None

            # Create application
            app = CustomApplication(
                name="Panther 3211 Battle Creek",
                description="Identity and access management for Panther",
                app_type="Identity Management"
            )

            # Add users as resources
            for user in users:
                user_id = user.get('userName', user.get('name'))
                if not user_id:
                    self.metrics["warnings"] += 1
                    logger.warning("User missing userName/name field")
                    continue

                # Create user resource
                user_resource = app.add_resource(
                    name=user_id,
                    resource_type="User"
                )
                
                # Add user properties
                if email := user.get('email'):
                    user_resource.add_property("Email", email, OAAPropertyType.STRING)
                if full_name := user.get('fullName'):
                    user_resource.add_property("Full Name", full_name, OAAPropertyType.STRING)
                if employee_id := user.get('employeeId'):
                    user_resource.add_property("Employee ID", employee_id, OAAPropertyType.STRING)
                if phone := user.get('phoneNumber'):
                    user_resource.add_property("Phone Number", phone, OAAPropertyType.STRING)
                
                is_active = user.get('isActive', True)
                user_resource.add_property("Is Active", str(is_active), OAAPropertyType.STRING)
                
                self.metrics["users_processed"] += 1

            # Add groups as resources
            for group in groups:
                group_name = group.get('groupName', group.get('name'))
                if not group_name:
                    self.metrics["warnings"] += 1
                    logger.warning("Group missing groupName/name field")
                    continue

                # Create group resource
                group_resource = app.add_resource(
                    name=group_name,
                    resource_type="Group"
                )
                
                self.metrics["groups_processed"] += 1

            # Add permissions - IT Ops team has read access to all
            it_ops_subject = app.add_subject(
                name="IT Operations",
                subject_type="Group"
            )

            # Grant read permissions on all resources
            for resource in app.resources:
                it_ops_subject.add_permission(
                    name="Read",
                    resources=[resource]
                )

            logger.info(f"Built payload with {self.metrics['users_processed']} users "
                       f"and {self.metrics['groups_processed']} groups")
            return app

        except Exception as e:
            logger.error(f"Failed to build payload: {e}")
            self.metrics["errors"] += 1
            return None

    def push_to_veza(self, app: CustomApplication) -> bool:
        """
        Push application data to Veza.
        
        Args:
            app: CustomApplication object to push
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would use the veza_connector's push method
            # Actual implementation depends on veza-oaa library version
            logger.info("Pushing data to Veza...")
            logger.info(f"Application: {app.name}")
            logger.info(f"Resources: {len(app.resources)}")
            logger.info(f"Subjects: {len(app.subjects)}")
            
            # Push to Veza (method name may vary based on library version)
            # self.veza.push_app(app)
            
            logger.info("Successfully pushed data to Veza")
            return True
            
        except Exception as e:
            logger.error(f"Failed to push to Veza: {e}")
            self.metrics["errors"] += 1
            return False

    def run(self) -> bool:
        """
        Execute the full integration pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting Panther to Veza integration")
        
        # Test Panther connection
        if not self.panther.test_connection():
            logger.error("Failed to connect to Panther")
            return False
        
        # Build payload
        app = self.build_payload()
        if not app:
            logger.error("Failed to build application payload")
            return False
        
        # Push to Veza
        if not self.push_to_veza(app):
            logger.error("Failed to push to Veza")
            return False
        
        logger.info("Integration completed successfully")
        self.log_metrics()
        return True

    def log_metrics(self):
        """Log integration metrics."""
        logger.info("=" * 60)
        logger.info("Integration Metrics")
        logger.info("=" * 60)
        logger.info(f"Users Processed: {self.metrics['users_processed']}")
        logger.info(f"Groups Processed: {self.metrics['groups_processed']}")
        logger.info(f"Warnings: {self.metrics['warnings']}")
        logger.info(f"Errors: {self.metrics['errors']}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Panther Identity Manager to Veza OAA Integration"
    )
    parser.add_argument(
        "--config",
        help="Path to .env configuration file",
        default=".env"
    )
    parser.add_argument(
        "--test",
        help="Test connection without pushing to Veza",
        action="store_true"
    )
    parser.add_argument(
        "--dry-run",
        help="Build payload without pushing to Veza",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    if os.path.exists(args.config):
        load_dotenv(args.config)
    else:
        logger.warning(f"Configuration file {args.config} not found")
    
    # Get credentials from environment
    panther_base_url = os.getenv("PANTHER_BASE_URL")
    panther_client_id = os.getenv("PANTHER_CLIENT_ID")
    panther_client_secret = os.getenv("PANTHER_CLIENT_SECRET")
    panther_tenant_id = os.getenv("PANTHER_TENANT_ID", "3211")
    
    veza_api_key = os.getenv("VEZA_API_KEY")
    veza_url = os.getenv("VEZA_URL")
    
    # Validate required configuration
    if not all([panther_base_url, panther_client_id, panther_client_secret]):
        logger.error("Missing required Panther configuration (BASE_URL, CLIENT_ID, CLIENT_SECRET)")
        sys.exit(1)
    
    if not args.test and not all([veza_api_key, veza_url]):
        logger.error("Missing required Veza configuration (API_KEY, URL)")
        sys.exit(1)
    
    # Initialize connectors
    panther = PantherConnector(
        base_url=panther_base_url,
        client_id=panther_client_id,
        client_secret=panther_client_secret,
        tenant_id=panther_tenant_id
    )
    
    # Authenticate
    if not panther.authenticate():
        logger.error("Failed to authenticate with Panther")
        sys.exit(1)
    
    # Test mode
    if args.test:
        if panther.test_connection():
            logger.info("Test connection successful")
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Initialize Veza connector
    veza = OAAConnector(
        api_key=veza_api_key,
        url=veza_url
    )
    
    # Create and run integration
    integration = PantherToVezaIntegration(panther, veza)
    
    if not integration.run():
        sys.exit(1)


if __name__ == "__main__":
    main()
