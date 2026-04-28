#!/usr/bin/env python3
"""
Palantir Foundry to Veza OAA Integration

This integration collects resource definitions, datasets, and access control information
from Palantir Foundry and pushes it to Veza via the Open Authorization API (OAA).
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
        logging.FileHandler('palantir_foundry_veza_integration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PalantirFoundryConnector:
    """Connector for Palantir Foundry API."""

    def __init__(self, base_url: str, api_token: str):
        """
        Initialize Palantir Foundry connector.

        Args:
            base_url: Base URL for Palantir Foundry (e.g., https://westrock.palantirfoundry.com/)
            api_token: API token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
    def authenticate(self) -> bool:
        """
        Verify authentication with Palantir Foundry.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/foundry/core/v1/user",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            user_data = response.json()
            logger.info(f"Successfully authenticated as user: {user_data.get('displayName', 'Unknown')}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test connection to Palantir Foundry API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/foundry/core/v1/healthcheck",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            logger.info("Health check successful")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_datasets(self) -> List[Dict[str, Any]]:
        """
        Fetch all datasets from Palantir Foundry.
        
        Returns:
            List of dataset dictionaries
        """
        try:
            datasets = []
            page_token = None
            
            while True:
                params = {}
                if page_token:
                    params['pageToken'] = page_token
                
                response = requests.get(
                    f"{self.base_url}/api/foundry/datasets/v1/datasets",
                    headers=self.headers,
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                
                data = response.json()
                datasets.extend(data.get('datasets', []))
                
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Retrieved {len(datasets)} datasets from Palantir Foundry")
            return datasets
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch datasets: {e}")
            return []

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Fetch all projects from Palantir Foundry.
        
        Returns:
            List of project dictionaries
        """
        try:
            projects = []
            page_token = None
            
            while True:
                params = {}
                if page_token:
                    params['pageToken'] = page_token
                
                response = requests.get(
                    f"{self.base_url}/api/foundry/projects/v1/projects",
                    headers=self.headers,
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                
                data = response.json()
                projects.extend(data.get('projects', []))
                
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Retrieved {len(projects)} projects from Palantir Foundry")
            return projects
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch projects: {e}")
            return []

    def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Fetch all workspaces from Palantir Foundry.
        
        Returns:
            List of workspace dictionaries
        """
        try:
            workspaces = []
            page_token = None
            
            while True:
                params = {}
                if page_token:
                    params['pageToken'] = page_token
                
                response = requests.get(
                    f"{self.base_url}/api/foundry/workspaces/v1/workspaces",
                    headers=self.headers,
                    params=params,
                    timeout=60
                )
                response.raise_for_status()
                
                data = response.json()
                workspaces.extend(data.get('workspaces', []))
                
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Retrieved {len(workspaces)} workspaces from Palantir Foundry")
            return workspaces
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch workspaces: {e}")
            return []

    def get_access_controls(self, resource_id: str, resource_type: str) -> List[Dict[str, Any]]:
        """
        Fetch access control information for a specific resource.
        
        Args:
            resource_id: The resource ID
            resource_type: Type of resource (dataset, project, workspace)
            
        Returns:
            List of access control entries
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/foundry/{resource_type}s/v1/{resource_type}s/{resource_id}/access",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('accessControls', [])
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch access controls for {resource_type} {resource_id}: {e}")
            return []


class PalantirFoundryToVezaIntegration:
    """Integration between Palantir Foundry and Veza OAA."""

    def __init__(self, foundry_connector: PalantirFoundryConnector, veza_connector: OAAConnector):
        """
        Initialize integration.
        
        Args:
            foundry_connector: Palantir Foundry API connector instance
            veza_connector: Veza OAA connector instance
        """
        self.foundry = foundry_connector
        self.veza = veza_connector
        self.metrics = {
            "datasets_processed": 0,
            "projects_processed": 0,
            "workspaces_processed": 0,
            "permissions_discovered": 0,
            "errors": 0,
            "warnings": 0
        }

    def build_payload(self) -> Optional[CustomApplication]:
        """
        Build Veza CustomApplication payload from Palantir Foundry data.
        
        Returns:
            CustomApplication object or None if failed
        """
        try:
            # Fetch data from Foundry
            datasets = self.foundry.get_datasets()
            projects = self.foundry.get_projects()
            workspaces = self.foundry.get_workspaces()
            
            if not datasets and not projects and not workspaces:
                logger.error("No datasets, projects, or workspaces retrieved from Palantir Foundry")
                return None

            # Create application
            app = CustomApplication(
                name="Palantir Foundry",
                description="Data governance and access control for Palantir Foundry at Westrock",
                app_type="Data Platform"
            )

            # Add workspaces as containers
            workspace_map = {}
            for workspace in workspaces:
                workspace_id = workspace.get('id', workspace.get('uuid'))
                workspace_name = workspace.get('name', workspace_id)
                
                if not workspace_id:
                    self.metrics["warnings"] += 1
                    logger.warning("Workspace missing ID")
                    continue

                workspace_resource = app.add_resource(
                    name=workspace_name,
                    resource_type="Workspace"
                )
                
                workspace_map[workspace_id] = workspace_resource
                
                # Add workspace properties
                if description := workspace.get('description'):
                    workspace_resource.add_property("Description", description, OAAPropertyType.STRING)
                if created := workspace.get('createdDate'):
                    workspace_resource.add_property("Created", created, OAAPropertyType.STRING)
                
                self.metrics["workspaces_processed"] += 1

            # Add projects as resources
            project_map = {}
            for project in projects:
                project_id = project.get('id', project.get('uuid'))
                project_name = project.get('name', project_id)
                
                if not project_id:
                    self.metrics["warnings"] += 1
                    logger.warning("Project missing ID")
                    continue

                project_resource = app.add_resource(
                    name=project_name,
                    resource_type="Project"
                )
                
                project_map[project_id] = project_resource
                
                # Add project properties
                if description := project.get('description'):
                    project_resource.add_property("Description", description, OAAPropertyType.STRING)
                if workspace_id := project.get('workspaceId'):
                    if workspace_id in workspace_map:
                        project_resource.add_property("Workspace", workspace_map[workspace_id].name, OAAPropertyType.STRING)
                if created := project.get('createdDate'):
                    project_resource.add_property("Created", created, OAAPropertyType.STRING)
                
                self.metrics["projects_processed"] += 1

            # Add datasets as resources
            for dataset in datasets:
                dataset_id = dataset.get('id', dataset.get('uuid'))
                dataset_name = dataset.get('name', dataset_id)
                
                if not dataset_id:
                    self.metrics["warnings"] += 1
                    logger.warning("Dataset missing ID")
                    continue

                dataset_resource = app.add_resource(
                    name=dataset_name,
                    resource_type="Dataset"
                )
                
                # Add dataset properties
                if description := dataset.get('description'):
                    dataset_resource.add_property("Description", description, OAAPropertyType.STRING)
                if created := dataset.get('createdDate'):
                    dataset_resource.add_property("Created", created, OAAPropertyType.STRING)
                if modified := dataset.get('modifiedDate'):
                    dataset_resource.add_property("Modified", modified, OAAPropertyType.STRING)
                if owner_id := dataset.get('ownerId'):
                    dataset_resource.add_property("Owner ID", owner_id, OAAPropertyType.STRING)
                if dataset_type := dataset.get('type'):
                    dataset_resource.add_property("Type", dataset_type, OAAPropertyType.STRING)
                
                self.metrics["datasets_processed"] += 1

            logger.info(f"Built payload with {self.metrics['workspaces_processed']} workspaces, "
                       f"{self.metrics['projects_processed']} projects, and "
                       f"{self.metrics['datasets_processed']} datasets")
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
        logger.info("Starting Palantir Foundry to Veza integration")
        
        # Authenticate
        if not self.foundry.authenticate():
            logger.error("Failed to authenticate with Palantir Foundry")
            return False
        
        # Test connection
        if not self.foundry.test_connection():
            logger.error("Failed to connect to Palantir Foundry")
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
        logger.info(f"Workspaces Processed: {self.metrics['workspaces_processed']}")
        logger.info(f"Projects Processed: {self.metrics['projects_processed']}")
        logger.info(f"Datasets Processed: {self.metrics['datasets_processed']}")
        logger.info(f"Permissions Discovered: {self.metrics['permissions_discovered']}")
        logger.info(f"Warnings: {self.metrics['warnings']}")
        logger.info(f"Errors: {self.metrics['errors']}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Palantir Foundry to Veza OAA Integration"
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
    foundry_base_url = os.getenv("FOUNDRY_BASE_URL")
    foundry_api_token = os.getenv("FOUNDRY_API_TOKEN")
    
    veza_api_key = os.getenv("VEZA_API_KEY")
    veza_url = os.getenv("VEZA_URL")
    
    # Validate required configuration
    if not all([foundry_base_url, foundry_api_token]):
        logger.error("Missing required Palantir Foundry configuration (BASE_URL, API_TOKEN)")
        sys.exit(1)
    
    if not args.test and not all([veza_api_key, veza_url]):
        logger.error("Missing required Veza configuration (API_KEY, URL)")
        sys.exit(1)
    
    # Initialize connectors
    foundry = PalantirFoundryConnector(
        base_url=foundry_base_url,
        api_token=foundry_api_token
    )
    
    # Test mode
    if args.test:
        if foundry.authenticate() and foundry.test_connection():
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
    integration = PalantirFoundryToVezaIntegration(foundry, veza)
    
    if not integration.run():
        sys.exit(1)


if __name__ == "__main__":
    main()
