#!/usr/bin/env python3
"""
Palantir Foundry to Veza OAA Integration Script

Collects resource definitions, datasets, workspaces, and access control information
from Palantir Foundry and pushes to Veza via the Open Authorization API (OAA).
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


class PalantirFoundryClient:
    """Palantir Foundry API client."""

    def __init__(self, base_url: str, api_token: str):
        """
        Initialize Palantir Foundry client.
        
        Args:
            base_url: Palantir Foundry base URL (e.g., https://westrock.palantirfoundry.com)
            api_token: API token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._test_connection()

    def _test_connection(self) -> None:
        """Test connection to Palantir Foundry API."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v2/admin/users",
                #f"{self.base_url}/api/foundry/core/v1/user",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            user_data = response.json()
            logger.info(
                f"Successfully authenticated with Palantir Foundry as: {user_data.get('displayName', 'Unknown')}"
            )
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Palantir Foundry: {e}")
            sys.exit(1)

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None
    ) -> Dict:
        """
        Make API request to Palantir Foundry.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
        """
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed ({method} {endpoint}): {e}")
            raise

    def get_paginated_results(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Fetch all results from paginated endpoint.
        
        Args:
            endpoint: API endpoint
            params: Query parameters (page token will be added)
            
        Returns:
            List of all items across pages
        """
        results = []
        page_token = None
        params = params or {}

        while True:
            if page_token:
                params["pageToken"] = page_token

            try:
                data = self._make_request("GET", endpoint, params=params)
                items_key = None

                # Determine items key based on endpoint
                if "datasets" in endpoint:
                    items_key = "datasets"
                elif "projects" in endpoint:
                    items_key = "projects"
                elif "workspaces" in endpoint:
                    items_key = "workspaces"
                elif "resources" in endpoint:
                    items_key = "resources"
                else:
                    items_key = "items"

                items = data.get(items_key, [])
                if not items:
                    break

                results.extend(items)
                page_token = data.get("nextPageToken")

                if not page_token:
                    break

            except requests.RequestException:
                logger.warning(
                    f"Pagination stopped; returning partial results ({len(results)} items)"
                )
                break

        return results

    def get_workspaces(self) -> List[Dict]:
        """
        Fetch all workspaces from Palantir Foundry.
        
        Returns:
            List of workspace dictionaries
        """
        logger.info("Fetching workspaces from Palantir Foundry...")
        try:
            workspaces = self.get_paginated_results("/api/foundry/workspaces/v1/workspaces")
            logger.info(f"Retrieved {len(workspaces)} workspaces")
            return workspaces
        except requests.RequestException:
            logger.error("Failed to fetch workspaces")
            return []

    def get_projects(self) -> List[Dict]:
        """
        Fetch all projects from Palantir Foundry.
        
        Returns:
            List of project dictionaries
        """
        logger.info("Fetching projects from Palantir Foundry...")
        try:
            projects = self.get_paginated_results("/api/foundry/projects/v1/projects")
            logger.info(f"Retrieved {len(projects)} projects")
            return projects
        except requests.RequestException:
            logger.error("Failed to fetch projects")
            return []

    def get_datasets(self) -> List[Dict]:
        """
        Fetch all datasets from Palantir Foundry.
        
        Returns:
            List of dataset dictionaries
        """
        logger.info("Fetching datasets from Palantir Foundry...")
        try:
            datasets = self.get_paginated_results("/api/foundry/datasets/v1/datasets")
            logger.info(f"Retrieved {len(datasets)} datasets")
            return datasets
        except requests.RequestException:
            logger.error("Failed to fetch datasets")
            return []

    def get_resources(self) -> List[Dict]:
        """
        Fetch all resources from Palantir Foundry.
        
        Returns:
            List of resource dictionaries
        """
        logger.info("Fetching resources from Palantir Foundry...")
        try:
            resources = self.get_paginated_results("/api/foundry/resources/v1/resources")
            logger.info(f"Retrieved {len(resources)} resources")
            return resources
        except requests.RequestException:
            logger.error("Failed to fetch resources")
            return []

    def get_access_policies(self, resource_id: str) -> List[Dict]:
        """
        Fetch access policies for a specific resource.
        
        Args:
            resource_id: The resource ID
            
        Returns:
            List of access policy dictionaries
        """
        try:
            endpoint = f"/api/foundry/resources/v1/resources/{resource_id}/access-policies"
            policies = self.get_paginated_results(endpoint)
            return policies
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch access policies for resource {resource_id}: {e}")
            return []


def build_oaa_payload(foundry_data: Dict) -> CustomApplication:
    """
    Build OAA CustomApplication from Palantir Foundry data.
    
    Args:
        foundry_data: Dictionary containing workspaces, projects, datasets, resources
        
    Returns:
        CustomApplication object with all entities and permissions
    """
    app = CustomApplication(
        name="Palantir Foundry",
        application_type="Data Platform",
    )

    # Add custom permission sets
    app.add_custom_permission("viewer", [OAAPermission.DataRead])
    app.add_custom_permission(
        "editor", [OAAPermission.DataRead, OAAPermission.DataWrite]
    )
    app.add_custom_permission(
        "admin",
        [
            OAAPermission.DataRead,
            OAAPermission.DataWrite,
            OAAPermission.MetadataRead,
            OAAPermission.MetadataWrite,
        ],
    )

    # Track resources for relationship mapping
    workspace_map = {}
    project_map = {}
    dataset_map = {}
    resource_map = {}

    # Process workspaces
    logger.info("Processing workspaces...")
    for workspace in foundry_data.get("workspaces", []):
        workspace_id = workspace.get("rid") or workspace.get("id")
        workspace_name = workspace.get("displayName", workspace.get("name", workspace_id))

        if not workspace_id:
            logger.warning("Workspace missing ID")
            continue

        resource = app.add_resource(
            resource_id=workspace_id,
            resource_name=workspace_name,
            resource_type="Workspace",
        )
        workspace_map[workspace_id] = resource

        # Add metadata properties
        if description := workspace.get("description"):
            resource.add_property("Description", description, "str")
        if owner := workspace.get("owner"):
            resource.add_property("Owner", owner, "str")
        if created := workspace.get("createdAt"):
            resource.add_property("Created", str(created), "str")

        logger.debug(f"Added workspace: {workspace_name} ({workspace_id})")

    # Process projects
    logger.info("Processing projects...")
    for project in foundry_data.get("projects", []):
        project_id = project.get("rid") or project.get("id")
        project_name = project.get("displayName", project.get("name", project_id))

        if not project_id:
            logger.warning("Project missing ID")
            continue

        resource = app.add_resource(
            resource_id=project_id,
            resource_name=project_name,
            resource_type="Project",
        )
        project_map[project_id] = resource

        # Add metadata properties
        if description := project.get("description"):
            resource.add_property("Description", description, "str")
        if workspace_rid := project.get("workspaceRid"):
            if workspace_rid in workspace_map:
                resource.add_property(
                    "Workspace", workspace_map[workspace_rid].name, "str"
                )
        if owner := project.get("owner"):
            resource.add_property("Owner", owner, "str")
        if created := project.get("createdAt"):
            resource.add_property("Created", str(created), "str")

        logger.debug(f"Added project: {project_name} ({project_id})")

    # Process datasets
    logger.info("Processing datasets...")
    for dataset in foundry_data.get("datasets", []):
        dataset_id = dataset.get("rid") or dataset.get("id")
        dataset_name = dataset.get("displayName", dataset.get("name", dataset_id))

        if not dataset_id:
            logger.warning("Dataset missing ID")
            continue

        resource = app.add_resource(
            resource_id=dataset_id,
            resource_name=dataset_name,
            resource_type="Dataset",
        )
        dataset_map[dataset_id] = resource

        # Add metadata properties
        if description := dataset.get("description"):
            resource.add_property("Description", description, "str")
        if project_rid := dataset.get("projectRid"):
            if project_rid in project_map:
                resource.add_property("Project", project_map[project_rid].name, "str")
        if owner := dataset.get("owner"):
            resource.add_property("Owner", owner, "str")
        if created := dataset.get("createdAt"):
            resource.add_property("Created", str(created), "str")
        if dataset_type := dataset.get("type"):
            resource.add_property("Type", dataset_type, "str")
        if row_count := dataset.get("rowCount"):
            resource.add_property("Row Count", str(row_count), "str")

        logger.debug(f"Added dataset: {dataset_name} ({dataset_id})")

    # Process generic resources
    logger.info("Processing resources...")
    for resource_data in foundry_data.get("resources", []):
        resource_id = resource_data.get("rid") or resource_data.get("id")
        resource_name = resource_data.get("displayName", resource_data.get("name", resource_id))
        resource_type = resource_data.get("type", "Resource")

        if not resource_id:
            logger.warning("Resource missing ID")
            continue

        resource = app.add_resource(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type=resource_type,
        )
        resource_map[resource_id] = resource

        # Add metadata properties
        if description := resource_data.get("description"):
            resource.add_property("Description", description, "str")
        if owner := resource_data.get("owner"):
            resource.add_property("Owner", owner, "str")
        if created := resource_data.get("createdAt"):
            resource.add_property("Created", str(created), "str")

        logger.debug(f"Added resource: {resource_name} ({resource_id})")

    logger.info(
        f"Built payload with {len(workspace_map)} workspaces, "
        f"{len(project_map)} projects, {len(dataset_map)} datasets, "
        f"and {len(resource_map)} resources"
    )
    return app


def push_to_veza(oaa_client: OAAClient, app: CustomApplication) -> bool:
    """
    Push application data to Veza.
    
    Args:
        oaa_client: Authenticated OAAClient instance
        app: CustomApplication object to push
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Pushing Palantir Foundry data to Veza...")
        logger.info(f"Application: {app.name}")
        logger.info(f"Resources: {len(app.resources)}")
        logger.info(f"Subjects: {len(app.subjects)}")

        response = oaa_client.push_application(
            app, delete_previous=True, provider_id="palantir-foundry"
        )

        logger.info(f"Successfully pushed data to Veza: {response}")
        return True

    except OAAClientError as e:
        logger.error(f"Failed to push to Veza: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Palantir Foundry to Veza OAA Integration"
    )
    parser.add_argument(
        "--config",
        help="Path to .env configuration file",
        default=".env",
    )
    parser.add_argument(
        "--test",
        help="Test connection without pushing to Veza",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        help="Build payload without pushing to Veza",
        action="store_true",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("palantir_foundry_veza_integration.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

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
        logger.error(
            "Missing required Palantir Foundry configuration (FOUNDRY_BASE_URL, FOUNDRY_API_TOKEN)"
        )
        sys.exit(1)

    if not args.test and not all([veza_api_key, veza_url]):
        logger.error(
            "Missing required Veza configuration (VEZA_API_KEY, VEZA_URL)"
        )
        sys.exit(1)

    # Initialize Palantir Foundry client
    logger.info("Initializing Palantir Foundry client...")
    foundry = PalantirFoundryClient(
        base_url=foundry_base_url, api_token=foundry_api_token
    )

    # Test mode
    if args.test:
        logger.info("Test mode: connection successful")
        sys.exit(0)

    # Fetch data from Palantir Foundry
    logger.info("Fetching data from Palantir Foundry...")
    foundry_data = {
        "workspaces": foundry.get_workspaces(),
        "projects": foundry.get_projects(),
        "datasets": foundry.get_datasets(),
        "resources": foundry.get_resources(),
    }

    # Build OAA payload
    logger.info("Building OAA payload...")
    app = build_oaa_payload(foundry_data)

    if args.dry_run:
        logger.info("Dry run mode: payload built successfully")
        logger.info(json.dumps(app.to_json(), indent=2))
        sys.exit(0)

    # Initialize Veza OAA client
    logger.info("Initializing Veza OAA client...")
    try:
        oaa_client = OAAClient(api_key=veza_api_key, url=veza_url)
    except OAAClientError as e:
        logger.error(f"Failed to initialize Veza client: {e}")
        sys.exit(1)

    # Push to Veza
    if push_to_veza(oaa_client, app):
        logger.info("Integration completed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to push data to Veza")
        sys.exit(1)


if __name__ == "__main__":
    main()
