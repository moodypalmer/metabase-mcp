#!/usr/bin/env python3
"""
Metabase FastMCP Server

A FastMCP server that provides tools to interact with Metabase databases,
execute queries, manage cards, and work with collections.
"""

import asyncio
import logging
import os
from enum import Enum
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Metabase configuration from environment variables
METABASE_URL = os.getenv("METABASE_URL")
METABASE_USER_EMAIL = os.getenv("METABASE_USER_EMAIL")
METABASE_PASSWORD = os.getenv("METABASE_PASSWORD")
METABASE_API_KEY = os.getenv("METABASE_API_KEY")

if not METABASE_URL or (
    not METABASE_API_KEY and (not METABASE_USER_EMAIL or not METABASE_PASSWORD)
):
    raise ValueError(
        "METABASE_URL is required, and either METABASE_API_KEY or both METABASE_USER_EMAIL and METABASE_PASSWORD must be provided"
    )


# Authentication method enum
class AuthMethod(Enum):
    SESSION = "session"
    API_KEY = "api_key"


# Visualization display types
class DisplayType(Enum):
    """Supported visualization types in Metabase"""
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    PIE = "pie"
    SCALAR = "scalar"
    SMARTSCALAR = "smartscalar"
    PROGRESS = "progress"
    GAUGE = "gauge"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"
    SCATTER = "scatter"
    MAP = "map"
    PIVOT = "pivot"
    COMBO = "combo"


# Initialize FastMCP server
mcp = FastMCP(name="metabase-mcp")


class MetabaseClient:
    """HTTP client for Metabase API operations"""

    def __init__(self):
        self.base_url = METABASE_URL.rstrip("/")
        self.session_token: str | None = None
        self.api_key: str | None = METABASE_API_KEY
        self.auth_method = AuthMethod.API_KEY if METABASE_API_KEY else AuthMethod.SESSION
        self.client = httpx.AsyncClient(timeout=30.0)

        logger.info(f"Using {self.auth_method.value} authentication method")

    async def _get_headers(self) -> dict[str, str]:
        """Get appropriate authentication headers"""
        headers = {"Content-Type": "application/json"}

        if self.auth_method == AuthMethod.API_KEY and self.api_key:
            headers["X-API-KEY"] = self.api_key
        elif self.auth_method == AuthMethod.SESSION:
            if not self.session_token:
                await self._get_session_token()
            if self.session_token:
                headers["X-Metabase-Session"] = self.session_token

        return headers

    async def _get_session_token(self) -> str:
        """Get Metabase session token for email/password authentication"""
        if self.auth_method == AuthMethod.API_KEY and self.api_key:
            return self.api_key

        if not METABASE_USER_EMAIL or not METABASE_PASSWORD:
            raise ValueError("Email and password required for session authentication")

        login_data = {"username": METABASE_USER_EMAIL, "password": METABASE_PASSWORD}

        response = await self.client.post(f"{self.base_url}/api/session", json=login_data)

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            raise Exception(f"Authentication failed: {response.status_code} - {error_data}")

        session_data = response.json()
        self.session_token = session_data.get("id")
        logger.info("Successfully obtained session token")
        return self.session_token

    async def request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make authenticated request to Metabase API"""
        url = f"{self.base_url}/api{path}"
        headers = await self._get_headers()

        logger.debug(f"Making {method} request to {path}")

        response = await self.client.request(method=method, url=url, headers=headers, **kwargs)

        if not response.is_success:
            error_data = response.json() if response.content else {}
            error_message = (
                f"API request failed with status {response.status_code}: {response.text}"
            )
            logger.warning(f"{error_message} - {error_data}")
            raise Exception(error_message)

        logger.debug(f"Successful response from {path}")
        
        # Handle empty responses (e.g., 204 No Content from DELETE endpoints)
        if response.status_code == 204 or not response.content:
            return {"success": True, "status": "204 No Content", "message": "Operation completed successfully"}
        
        return response.json()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global client instance
metabase_client = MetabaseClient()


# Tool implementations
@mcp.tool
async def list_databases() -> dict[str, Any]:
    """List all databases in Metabase"""
    try:
        result = await metabase_client.request("GET", "/database")
        return result
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        raise


@mcp.tool
async def list_cards(
    limit: int = 50,
    offset: int = 0,
    f: str | None = None,
    model_type: str | None = None
) -> dict[str, Any]:
    """List questions/cards in Metabase with client-side pagination
    
    Note: The Metabase API returns ALL cards, so pagination is applied client-side.
    For better performance with large instances, consider using list_collection_items().
    
    Args:
        limit: Maximum number of cards to return (default: 50, 0 = all)
        offset: Number of cards to skip (default: 0)
        f: Filter - "all", "mine", "archived", "using_model", "using_metric" (default: all)
        model_type: Filter by type - "card", "model", "metric" (returns all types if not specified)
    """
    try:
        # Build query parameters for filtering
        params = []
        if f:
            params.append(f"f={f}")
        if model_type:
            params.append(f"model_type={model_type}")
            
        query_string = "&".join(params) if params else ""
        endpoint = f"/card?{query_string}" if query_string else "/card"
        
        # Get all cards from the API
        all_cards = await metabase_client.request("GET", endpoint)
        
        # Ensure we have a list
        if not isinstance(all_cards, list):
            logger.warning("Unexpected response format from /api/card endpoint")
            return all_cards
        
        total_count = len(all_cards)
        
        # Apply client-side pagination
        if limit > 0:
            paginated_cards = all_cards[offset:offset + limit]
        else:
            # limit = 0 means return all
            paginated_cards = all_cards[offset:]
        
        # Return in a format similar to other paginated endpoints
        result = {
            "data": paginated_cards,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
        # Add a warning for large datasets
        if total_count > 1000:
            logger.warning(
                f"Retrieved {total_count} cards from Metabase. "
                f"Consider using list_collection_items() for better performance."
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing cards: {e}")
        raise


@mcp.tool
async def execute_card(card_id: int, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a Metabase question/card and get results"""
    try:
        payload = {}
        if parameters:
            payload["parameters"] = parameters

        result = await metabase_client.request("POST", f"/card/{card_id}/query", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error executing card {card_id}: {e}")
        raise


@mcp.tool
async def execute_query(
    database_id: int, query: str, native_parameters: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Execute a SQL query against a Metabase database"""
    try:
        payload = {"database": database_id, "type": "native", "native": {"query": query}}

        if native_parameters:
            payload["native"]["parameters"] = native_parameters

        result = await metabase_client.request("POST", "/dataset", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise


def create_text_filter(name: str, display_name: str | None = None, default: str | None = None) -> tuple[dict, dict]:
    """Helper function to create a text filter parameter and template tag
    
    Args:
        name: The variable name (used in SQL as {{name}})
        display_name: Display name for the filter widget (defaults to name)
        default: Default value for the filter
        
    Returns:
        Tuple of (parameter_dict, template_tag_dict)
    """
    import uuid
    filter_id = str(uuid.uuid4())
    
    parameter = {
        "id": filter_id,
        "name": display_name or name,
        "slug": name,
        "type": "string/="
    }
    
    if default:
        parameter["default"] = default
    
    template_tag = {
        "id": filter_id,
        "name": name,
        "display-name": display_name or name,
        "type": "text"
    }
    
    if default:
        template_tag["default"] = default
        
    return parameter, template_tag


def create_field_filter(name: str, display_name: str | None = None, field_ref: list | None = None) -> tuple[dict, dict]:
    """Helper function to create a field filter parameter and template tag
    
    Args:
        name: The variable name (used in SQL as {{name}})
        display_name: Display name for the filter widget (defaults to name)
        field_ref: Field reference for the filter (e.g., ["field", 123, None])
        
    Returns:
        Tuple of (parameter_dict, template_tag_dict)
    """
    import uuid
    filter_id = str(uuid.uuid4())
    
    parameter = {
        "id": filter_id,
        "name": display_name or name,
        "slug": name,
        "type": "category"  # Can be adjusted based on field type
    }
    
    if field_ref:
        parameter["target"] = ["dimension", ["template-tag", name]]
    
    template_tag = {
        "id": filter_id,
        "name": name,
        "display-name": display_name or name,
        "type": "dimension"
    }
    
    if field_ref:
        template_tag["dimension"] = field_ref
        
    return parameter, template_tag


# Visualization settings helper functions
def create_table_visualization(
    pivot_column: str | None = None,
    cell_column: str | None = None,
    column_settings: dict[str, dict[str, Any]] | None = None,
    table_columns: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create visualization settings for table displays
    
    Args:
        pivot_column: Column to use for pivoting
        cell_column: Column values to display in cells
        column_settings: Per-column display settings
        table_columns: Column ordering and visibility settings
        
    Returns:
        Dictionary of table visualization settings
    """
    settings = {}
    
    if pivot_column:
        settings["table.pivot_column"] = pivot_column
    if cell_column:
        settings["table.cell_column"] = cell_column
    if column_settings:
        settings["column_settings"] = column_settings
    if table_columns:
        settings["table.columns"] = table_columns
        
    return settings


def create_graph_visualization(
    dimensions: list[str],
    metrics: list[str],
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
    show_values: bool = True,
    stacked: bool = False,
    area: bool = False
) -> dict[str, Any]:
    """Create visualization settings for graph displays (line, bar, area)
    
    Args:
        dimensions: List of dimension fields (x-axis)
        metrics: List of metric fields (y-axis)
        x_axis_title: Custom x-axis label
        y_axis_title: Custom y-axis label
        show_values: Whether to show data point values
        stacked: Whether to stack series
        area: Whether to fill area under lines
        
    Returns:
        Dictionary of graph visualization settings
    """
    settings = {
        "graph.dimensions": dimensions,
        "graph.metrics": metrics,
        "graph.show_values": show_values
    }
    
    if x_axis_title:
        settings["graph.x_axis.title_text"] = x_axis_title
    if y_axis_title:
        settings["graph.y_axis.title_text"] = y_axis_title
    if stacked:
        settings["stackable.stack_type"] = "stacked"
    if area:
        settings["line.interpolate"] = "cardinal"
        settings["area"] = True
        
    return settings


def create_pie_visualization(
    dimension: str,
    metric: str,
    show_legend: bool = True,
    show_total: bool = True,
    percentages: bool = True
) -> dict[str, Any]:
    """Create visualization settings for pie/donut charts
    
    Args:
        dimension: Field to use for pie slices
        metric: Field to use for values
        show_legend: Whether to show legend
        show_total: Whether to show total in center (donut)
        percentages: Whether to show percentages
        
    Returns:
        Dictionary of pie visualization settings
    """
    return {
        "pie.dimension": dimension,
        "pie.metric": metric,
        "pie.show_legend": show_legend,
        "pie.show_total": show_total,
        "pie.percent_visibility": "inside" if percentages else "off"
    }


def create_scalar_visualization(
    field: str,
    prefix: str | None = None,
    suffix: str | None = None,
    decimals: int | None = None,
    multiply_by: float | None = None,
    compact: bool = False
) -> dict[str, Any]:
    """Create visualization settings for scalar (single number) displays
    
    Args:
        field: Field to display
        prefix: Text to show before the number (e.g., "$")
        suffix: Text to show after the number (e.g., "%")
        decimals: Number of decimal places
        multiply_by: Multiply the value by this number
        compact: Use compact number formatting (e.g., 1.2K)
        
    Returns:
        Dictionary of scalar visualization settings
    """
    settings = {
        "scalar.field": field,
        "number_style": "decimal"
    }
    
    if prefix:
        settings["prefix"] = prefix
    if suffix:
        settings["suffix"] = suffix
    if decimals is not None:
        settings["decimals"] = decimals
    if multiply_by:
        settings["scale"] = multiply_by
    if compact:
        settings["compact"] = True
        
    return settings


def create_gauge_visualization(
    field: str,
    min_value: float = 0,
    max_value: float = 100,
    segments: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create visualization settings for gauge charts
    
    Args:
        field: Field to display
        min_value: Minimum value for gauge
        max_value: Maximum value for gauge
        segments: Color segments (e.g., [{"min": 0, "max": 60, "color": "#ED6E6E", "label": "Poor"}])
        
    Returns:
        Dictionary of gauge visualization settings
    """
    settings = {
        "gauge.field": field,
        "gauge.min": min_value,
        "gauge.max": max_value
    }
    
    if segments:
        settings["gauge.segments"] = segments
        
    return settings


@mcp.tool
async def create_card(
    name: str,
    database_id: int,
    query: str,
    description: str | None = None,
    collection_id: int | None = None,
    visualization_settings: dict[str, Any] | None = None,
    display: str = "table",
    dataset: bool = False,
    type: str | None = None,
    result_metadata: list[dict[str, Any]] | None = None,
    cache_ttl: int | None = None,
    query_type: str = "native",
    parameters: list[dict[str, Any]] | None = None,
    template_tags: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create a new question/card or model in Metabase
    
    Args:
        name: Name of the card/model
        database_id: Database ID to query
        query: SQL query or structured query (can contain {{variable}} placeholders)
        description: Optional description
        collection_id: Collection to place the card in
        visualization_settings: Visualization configuration dictionary
        display: Display type (table, bar, line, area, pie, scalar, etc.)
        dataset: Whether this is a model (True) or card (False)
        type: Explicitly set type ("question", "model", "metric")
        result_metadata: Column metadata for models
        cache_ttl: Cache time-to-live in seconds
        query_type: Query type - "native" for SQL, "query" for GUI query builder
        parameters: List of parameter definitions for filters
        template_tags: Template tag definitions for SQL variables
        
    Visualization Settings Examples:
        Table with pivot:
            visualization_settings = {
                "table.pivot_column": "category",
                "table.cell_column": "total_amount"
            }
            
        Bar chart:
            visualization_settings = {
                "graph.dimensions": ["month"],
                "graph.metrics": ["revenue", "profit"],
                "graph.x_axis.title_text": "Month",
                "graph.y_axis.title_text": "Amount ($)"
            }
            
        Pie chart:
            visualization_settings = {
                "pie.dimension": "product_category",
                "pie.metric": "sales_count",
                "pie.show_legend": True
            }
            
        Scalar (single number):
            visualization_settings = {
                "scalar.field": "total_revenue",
                "prefix": "$",
                "decimals": 2,
                "compact": True
            }
            
        You can also use the helper functions:
            visualization_settings = create_graph_visualization(
                dimensions=["date"],
                metrics=["sales"],
                stacked=True
            )
    """
    try:
        payload = {
            "name": name,
            "database_id": database_id,
            "display": display,
            "visualization_settings": visualization_settings or {},
            "dataset": dataset
        }
        
        # Handle query based on type
        if query_type == "native":
            native_query = {"query": query}
            
            # Add template tags if provided
            if template_tags:
                native_query["template-tags"] = template_tags
                
            payload["dataset_query"] = {
                "database": database_id,
                "type": "native",
                "native": native_query
            }
        else:
            # For structured queries (GUI query builder)
            payload["dataset_query"] = query if isinstance(query, dict) else {
                "database": database_id,
                "type": "query",
                "query": query
            }

        if description:
            payload["description"] = description
        if collection_id is not None:
            payload["collection_id"] = collection_id
        if type:
            payload["type"] = type
        if result_metadata:
            payload["result_metadata"] = result_metadata
        if cache_ttl is not None:
            payload["cache_ttl"] = cache_ttl
        if parameters:
            payload["parameters"] = parameters

        result = await metabase_client.request("POST", "/card", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error creating card: {e}")
        raise


@mcp.tool
async def list_collections(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """List all collections in Metabase
    
    Args:
        limit: Maximum number of collections to return (default: 50)
        offset: Number of collections to skip (default: 0)
    """
    try:
        params = f"?limit={limit}&offset={offset}"
        result = await metabase_client.request("GET", f"/collection{params}")
        return result
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise


@mcp.tool
async def create_collection(
    name: str,
    description: str | None = None,
    color: str | None = None,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Create a new collection in Metabase"""
    try:
        payload = {"name": name}

        if description:
            payload["description"] = description
        if color:
            payload["color"] = color
        if parent_id is not None:
            payload["parent_id"] = parent_id

        result = await metabase_client.request("POST", "/collection", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise


@mcp.tool
async def list_tables(database_id: int) -> str:
    """List all tables in a database with formatted markdown output"""
    try:
        result = await metabase_client.request("GET", f"/database/{database_id}/metadata")
        
        # Extract tables from the metadata response
        tables = result.get("tables", [])
        
        # Format tables with only the requested fields: table_id, display_name, description, entity_type
        formatted_tables = []
        for table in tables:
            table_info = {
                "table_id": table.get("id"),
                "display_name": table.get("display_name"),
                "description": table.get("description") or "No description",
                "entity_type": table.get("entity_type")
            }
            formatted_tables.append(table_info)
        
        # Sort by display_name for better readability
        formatted_tables.sort(key=lambda x: x.get("display_name", ""))
        
        # Generate markdown output
        markdown_output = f"# Tables in Database {database_id}\n\n"
        markdown_output += f"**Total Tables:** {len(formatted_tables)}\n\n"
        
        if not formatted_tables:
            markdown_output += "*No tables found in this database.*\n"
            return markdown_output
        
        # Create markdown table
        markdown_output += "| Table ID | Display Name | Description | Entity Type |\n"
        markdown_output += "|----------|--------------|-------------|--------------|\n"
        
        for table in formatted_tables:
            table_id = table.get("table_id", "N/A")
            display_name = table.get("display_name", "N/A")
            description = table.get("description", "No description")
            entity_type = table.get("entity_type", "N/A")
            
            # Escape pipe characters in content to prevent table formatting issues
            description = description.replace("|", "\\|")
            display_name = display_name.replace("|", "\\|")
            
            markdown_output += f"| {table_id} | {display_name} | {description} | {entity_type} |\n"
        
        return markdown_output
        
    except Exception as e:
        logger.error(f"Error listing tables for database {database_id}: {e}")
        raise


@mcp.tool
async def list_collection_items(
    collection_id: str | int = "root",
    limit: int = 50,
    offset: int = 0,
    models: list[str] | None = None,
    archived: bool = False,
    pinned_state: str | None = None,
    sort_column: str = "name",
    sort_direction: str = "asc"
) -> dict[str, Any]:
    """List items in a collection with pagination and filtering
    
    Args:
        collection_id: Collection ID or "root" for root collection (default: "root")
        limit: Maximum number of items to return (default: 50)
        offset: Number of items to skip (default: 0)
        models: List of model types to filter by (e.g., ["card", "dashboard", "collection"])
        archived: Whether to include archived items (default: False)
        pinned_state: Filter by pinned state ("is_pinned", "is_not_pinned", or None for all)
        sort_column: Column to sort by (default: "name")
        sort_direction: Sort direction "asc" or "desc" (default: "asc")
    """
    try:
        # Build query parameters
        params = [
            f"limit={limit}",
            f"offset={offset}",
            f"archived={str(archived).lower()}",
            f"sort_column={sort_column}",
            f"sort_direction={sort_direction}"
        ]
        
        if models:
            # Add each model as a separate parameter
            for model in models:
                params.append(f"models={model}")
        
        if pinned_state:
            params.append(f"pinned_state={pinned_state}")
        
        query_string = "&".join(params)
        
        # Handle root collection specially
        endpoint = f"/collection/{collection_id}/items" if collection_id != "root" else "/collection/root/items"
        
        result = await metabase_client.request("GET", f"{endpoint}?{query_string}")
        return result
    except Exception as e:
        logger.error(f"Error listing collection items for collection {collection_id}: {e}")
        raise


@mcp.tool
async def create_dashboard(
    name: str,
    description: str | None = None,
    collection_id: int | None = None,
    parameters: list[dict[str, Any]] | None = None,
    cache_ttl: int | None = None,
    position: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a new dashboard in Metabase
    
    Args:
        name: Dashboard name
        description: Dashboard description
        collection_id: Collection ID to place the dashboard in
        parameters: List of dashboard parameters for filtering
        cache_ttl: Cache time-to-live in seconds
        position: Collection position information
    """
    try:
        payload = {
            "name": name
        }
        
        if description:
            payload["description"] = description
        if collection_id is not None:
            payload["collection_id"] = collection_id
        if parameters:
            payload["parameters"] = parameters
        if cache_ttl is not None:
            payload["cache_ttl"] = cache_ttl
        if position:
            payload["collection_position"] = position
            
        result = await metabase_client.request("POST", "/dashboard", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error creating dashboard: {e}")
        raise


@mcp.tool
async def list_dashboards(
    collection_id: str | int = "root",
    limit: int = 50,
    offset: int = 0,
    archived: bool = False
) -> dict[str, Any]:
    """List dashboards in a collection
    
    Note: The /api/dashboard endpoint is deprecated. This uses the collection items endpoint.
    
    Args:
        collection_id: Collection ID or "root" for root collection (default: "root")
        limit: Maximum number of dashboards to return (default: 50)
        offset: Number of dashboards to skip (default: 0)
        archived: Whether to include archived dashboards (default: False)
    """
    try:
        # Build query parameters
        params = [
            f"limit={limit}",
            f"offset={offset}",
            f"archived={str(archived).lower()}",
            "models=dashboard"  # Single model filter for dashboards
        ]
        
        query_string = "&".join(params)
        
        # Handle root collection specially
        endpoint = f"/collection/{collection_id}/items" if collection_id != "root" else "/collection/root/items"
        
        result = await metabase_client.request("GET", f"{endpoint}?{query_string}")
        return result
    except Exception as e:
        logger.error(f"Error listing dashboards: {e}")
        raise


@mcp.tool
async def get_dashboard(dashboard_id: int) -> dict[str, Any]:
    """Get details of a specific dashboard including its cards
    
    Args:
        dashboard_id: The ID of the dashboard
    """
    try:
        result = await metabase_client.request("GET", f"/dashboard/{dashboard_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def update_dashboard(
    dashboard_id: int,
    name: str | None = None,
    description: str | None = None,
    parameters: list[dict[str, Any]] | None = None,
    cache_ttl: int | None = None,
    collection_id: int | None = None,
    position: dict[str, Any] | None = None,
    archived: bool | None = None
) -> dict[str, Any]:
    """Update an existing dashboard
    
    Args:
        dashboard_id: The ID of the dashboard to update
        name: New dashboard name
        description: New dashboard description
        parameters: Updated dashboard parameters
        cache_ttl: Updated cache time-to-live in seconds
        collection_id: Move dashboard to different collection
        position: Updated collection position
        archived: Archive/unarchive the dashboard
    """
    try:
        # Get current dashboard to preserve existing values
        current = await metabase_client.request("GET", f"/dashboard/{dashboard_id}")
        
        payload = {}
        
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if parameters is not None:
            payload["parameters"] = parameters
        if cache_ttl is not None:
            payload["cache_ttl"] = cache_ttl
        if collection_id is not None:
            payload["collection_id"] = collection_id
        if position is not None:
            payload["collection_position"] = position
        if archived is not None:
            payload["archived"] = archived
            
        result = await metabase_client.request("PUT", f"/dashboard/{dashboard_id}", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error updating dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def add_card_to_dashboard(
    dashboard_id: int,
    card_id: int,
    row: int = 0,
    col: int = 0,
    size_x: int = 4,
    size_y: int = 4,
    parameter_mappings: list[dict[str, Any]] | None = None,
    visualization_settings: dict[str, Any] | None = None,
    series: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Add a card to a dashboard
    
    Args:
        dashboard_id: The ID of the dashboard
        card_id: The ID of the card to add (use -1 for text cards)
        row: Row position (0-based)
        col: Column position (0-based)  
        size_x: Width in grid units (default: 4)
        size_y: Height in grid units (default: 4)
        parameter_mappings: Parameter mappings for dashboard filters
        visualization_settings: Visualization settings for this card
        series: Additional series to add to the card
    """
    try:
        # Build the dashcard payload
        payload = {
            "cardId": card_id,
            "row": row,
            "col": col,
            "size_x": size_x,
            "size_y": size_y
        }
        
        if parameter_mappings:
            payload["parameter_mappings"] = parameter_mappings
        if visualization_settings:
            payload["visualization_settings"] = visualization_settings
        if series:
            payload["series"] = series
            
        # Use POST to /api/dashboard/:id/dashcard to add a card
        result = await metabase_client.request("POST", f"/dashboard/{dashboard_id}/dashcard", json=payload)
        
        return result
    except Exception as e:
        logger.error(f"Error adding card {card_id} to dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def remove_card_from_dashboard(
    dashboard_id: int,
    dashcard_id: int
) -> dict[str, Any]:
    """Remove a card from a dashboard
    
    Note: This uses the PUT /api/dashboard/:id/cards endpoint to update the cards array
    
    Args:
        dashboard_id: The ID of the dashboard
        dashcard_id: The ID of the dashboard card (not the card ID itself)
    """
    try:
        # Get current dashboard to find existing cards
        dashboard = await metabase_client.request("GET", f"/dashboard/{dashboard_id}")
        existing_cards = dashboard.get("dashcards", [])
        
        # Filter out the card we want to remove
        updated_cards = [card for card in existing_cards if card.get("id") != dashcard_id]
        
        # Check if we actually found and removed a card
        if len(updated_cards) == len(existing_cards):
            raise Exception(f"Dashboard card {dashcard_id} not found in dashboard {dashboard_id}")
        
        # Update the dashboard with the filtered cards
        payload = {
            "cards": updated_cards
        }
        
        result = await metabase_client.request("PUT", f"/dashboard/{dashboard_id}/cards", json=payload)
        
        return {
            "success": True,
            "message": f"Card {dashcard_id} removed from dashboard {dashboard_id}",
            "remaining_cards": len(updated_cards)
        }
    except Exception as e:
        logger.error(f"Error removing card {dashcard_id} from dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def export_card(
    card_id: int,
    parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute a card/question and get results as JSON
    
    Args:
        card_id: The ID of the card to export
        parameters: Parameters to pass to the card
    """
    try:
        # This is the same as execute_card but named export for clarity
        payload = {}
        if parameters:
            payload["parameters"] = parameters
        
        result = await metabase_client.request("POST", f"/card/{card_id}/query", json=payload)
        return result
            
    except Exception as e:
        logger.error(f"Error exporting card {card_id}: {e}")
        raise


@mcp.tool
async def export_dashboard_structure(
    dashboard_id: int,
    include_card_results: bool = False
) -> dict[str, Any]:
    """Export dashboard structure and optionally card results as JSON
    
    Args:
        dashboard_id: The ID of the dashboard to export
        include_card_results: Whether to include query results for each card
    """
    try:
        # Get dashboard structure
        dashboard = await metabase_client.request("GET", f"/dashboard/{dashboard_id}")
        
        export_data = {
            "dashboard": {
                "id": dashboard.get("id"),
                "name": dashboard.get("name"),
                "description": dashboard.get("description"),
                "parameters": dashboard.get("parameters", []),
                "collection_id": dashboard.get("collection_id"),
                "cache_ttl": dashboard.get("cache_ttl"),
                "created_at": dashboard.get("created_at"),
                "updated_at": dashboard.get("updated_at")
            },
            "dashcards": []
        }
        
        # Process each dashcard
        for dashcard in dashboard.get("dashcards", []):
            card_data = {
                "id": dashcard.get("id"),
                "card_id": dashcard.get("card_id"),
                "row": dashcard.get("row"),
                "col": dashcard.get("col"),
                "size_x": dashcard.get("size_x"),
                "size_y": dashcard.get("size_y"),
                "parameter_mappings": dashcard.get("parameter_mappings", []),
                "visualization_settings": dashcard.get("visualization_settings", {})
            }
            
            # Optionally fetch card results
            if include_card_results and dashcard.get("card_id"):
                try:
                    # Execute the card query in dashboard context
                    results = await metabase_client.request(
                        "POST",
                        f"/dashboard/{dashboard_id}/dashcard/{dashcard['id']}/card/{dashcard['card_id']}/query"
                    )
                    card_data["results"] = results
                except Exception as e:
                    logger.warning(f"Could not fetch results for card {dashcard.get('card_id')}: {e}")
                    card_data["results"] = {"error": str(e)}
            
            export_data["dashcards"].append(card_data)
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def export_collection(
    collection_id: int,
    include_subcollections: bool = True
) -> dict[str, Any]:
    """Export a collection's structure and metadata
    
    Args:
        collection_id: The ID of the collection to export
        include_subcollections: Whether to include subcollections (default: True)
    """
    try:
        # Get collection details
        collection = await metabase_client.request("GET", f"/collection/{collection_id}")
        
        # Get all items in the collection
        items = await metabase_client.request(
            "GET", 
            f"/collection/{collection_id}/items?limit=1000"
        )
        
        export_data = {
            "collection": collection,
            "items": items.get("data", []),
            "total_items": items.get("total", 0)
        }
        
        # If including subcollections, recursively fetch them
        if include_subcollections:
            subcollections = []
            for item in items.get("data", []):
                if item.get("model") == "collection":
                    sub_export = await export_collection(
                        item["id"], 
                        include_subcollections=True
                    )
                    subcollections.append(sub_export)
            
            if subcollections:
                export_data["subcollections"] = subcollections
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting collection {collection_id}: {e}")
        raise


@mcp.tool
async def create_dashboard_parameter(
    dashboard_id: int,
    name: str,
    slug: str,
    type: str,
    default: Any = None,
    required: bool = False,
    values_query_type: str | None = None,
    values_source_type: str | None = None,
    values_source_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Add a parameter (filter) to an existing dashboard
    
    Args:
        dashboard_id: The ID of the dashboard
        name: Display name of the parameter
        slug: URL-friendly identifier for the parameter
        type: Parameter type (e.g., "date/range", "category", "location/state", etc.)
        default: Default value for the parameter
        required: Whether the parameter is required
        values_query_type: How to fetch values ("list", "search", "none")
        values_source_type: Source type for values ("card", "static-list", etc.)
        values_source_config: Configuration for the values source
    """
    try:
        # Get current dashboard
        dashboard = await metabase_client.request("GET", f"/dashboard/{dashboard_id}")
        
        # Create new parameter
        new_param = {
            "id": slug,  # ID is typically the same as slug
            "name": name,
            "slug": slug,
            "type": type
        }
        
        if default is not None:
            new_param["default"] = default
        if required:
            new_param["required"] = required
        if values_query_type:
            new_param["values_query_type"] = values_query_type
        if values_source_type:
            new_param["values_source_type"] = values_source_type
        if values_source_config:
            new_param["values_source_config"] = values_source_config
        
        # Add to existing parameters
        existing_params = dashboard.get("parameters", [])
        updated_params = existing_params + [new_param]
        
        # Update dashboard with new parameters
        result = await metabase_client.request(
            "PUT", 
            f"/dashboard/{dashboard_id}",
            json={"parameters": updated_params}
        )
        
        return result
    except Exception as e:
        logger.error(f"Error creating dashboard parameter: {e}")
        raise




@mcp.tool
async def get_card(card_id: int) -> dict[str, Any]:
    """Get details of a specific card/question
    
    Args:
        card_id: The ID of the card
    """
    try:
        result = await metabase_client.request("GET", f"/card/{card_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting card {card_id}: {e}")
        raise


@mcp.tool
async def update_card(
    card_id: int,
    name: str | None = None,
    description: str | None = None,
    query: str | dict[str, Any] | None = None,
    display: str | None = None,
    visualization_settings: dict[str, Any] | None = None,
    archived: bool | None = None,
    collection_id: int | None = None,
    result_metadata: list[dict[str, Any]] | None = None,
    cache_ttl: int | None = None,
    enable_embedding: bool | None = None,
    embedding_params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Update an existing card/question
    
    Args:
        card_id: The ID of the card to update
        name: New name for the card
        description: New description
        query: Updated SQL query or structured query
        display: Display type (table, bar, line, area, pie, scalar, etc.)
        visualization_settings: Visualization configuration dictionary (see create_card for examples)
        archived: Archive/unarchive the card
        collection_id: Move to different collection
        result_metadata: Column metadata for models
        cache_ttl: Cache time-to-live in seconds
        enable_embedding: Enable embedding for this card
        embedding_params: Embedding parameters configuration
        
    Example:
        # Update card to be a bar chart
        await update_card(
            card_id=123,
            display="bar",
            visualization_settings={
                "graph.dimensions": ["month"],
                "graph.metrics": ["sales"],
                "graph.y_axis.title_text": "Sales ($)"
            }
        )
    """
    try:
        payload = {}
        
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if query is not None:
            if isinstance(query, str):
                # Get current card to preserve database_id
                current_card = await metabase_client.request("GET", f"/card/{card_id}")
                payload["dataset_query"] = {
                    "database": current_card["database_id"],
                    "type": "native",
                    "native": {"query": query}
                }
            else:
                payload["dataset_query"] = query
        if display is not None:
            payload["display"] = display
        if visualization_settings is not None:
            payload["visualization_settings"] = visualization_settings
        if archived is not None:
            payload["archived"] = archived
        if collection_id is not None:
            payload["collection_id"] = collection_id
        if result_metadata is not None:
            payload["result_metadata"] = result_metadata
        if cache_ttl is not None:
            payload["cache_ttl"] = cache_ttl
        if enable_embedding is not None:
            payload["enable_embedding"] = enable_embedding
        if embedding_params is not None:
            payload["embedding_params"] = embedding_params
        
        result = await metabase_client.request("PUT", f"/card/{card_id}", json=payload)
        return result
    except Exception as e:
        logger.error(f"Error updating card {card_id}: {e}")
        raise


@mcp.tool
async def create_card_with_filters(
    name: str,
    database_id: int,
    query: str,
    filters: list[dict[str, Any]],
    description: str | None = None,
    collection_id: int | None = None,
    visualization_settings: dict[str, Any] | None = None,
    display: str = "table"
) -> dict[str, Any]:
    """Create a card with filters in a more user-friendly way
    
    Args:
        name: Name of the card
        database_id: Database ID to query
        query: SQL query with {{filter_name}} placeholders
        filters: List of filter definitions, each containing:
            - name: Variable name used in SQL
            - display_name: Display name for the filter widget (optional)
            - type: "text" or "field" (defaults to "text")
            - default: Default value (optional)
            - field_ref: Field reference for field filters (optional)
        description: Optional description
        collection_id: Collection to place the card in
        visualization_settings: Visualization configuration dictionary (see create_card for examples)
        display: Display type (table, bar, line, area, pie, scalar, etc.)
        
    Example:
        # Create a filtered sales report with bar chart visualization
        await create_card_with_filters(
            name="Sales by Category",
            database_id=1,
            query="SELECT category, SUM(amount) as total FROM sales WHERE 1=1 [[AND category = {{category}}]] GROUP BY category",
            filters=[
                {"name": "category", "display_name": "Product Category", "type": "text", "default": "Electronics"}
            ],
            display="bar",
            visualization_settings={
                "graph.dimensions": ["category"],
                "graph.metrics": ["total"],
                "graph.y_axis.title_text": "Total Sales ($)"
            }
        )
        
        # Using helper functions for visualization
        await create_card_with_filters(
            name="Revenue Dashboard",
            database_id=1,
            query="SELECT date, revenue FROM daily_stats WHERE date >= {{start_date}}",
            filters=[
                {"name": "start_date", "display_name": "Start Date", "type": "text", "default": "2024-01-01"}
            ],
            display="line",
            visualization_settings=create_graph_visualization(
                dimensions=["date"],
                metrics=["revenue"],
                x_axis_title="Date",
                y_axis_title="Revenue ($)",
                area=True
            )
        )
    """
    try:
        parameters = []
        template_tags = {}
        
        for filter_def in filters:
            filter_name = filter_def["name"]
            display_name = filter_def.get("display_name", filter_name)
            filter_type = filter_def.get("type", "text")
            default = filter_def.get("default")
            field_ref = filter_def.get("field_ref")
            
            if filter_type == "field":
                param, tag = create_field_filter(filter_name, display_name, field_ref)
            else:
                param, tag = create_text_filter(filter_name, display_name, default)
                
            parameters.append(param)
            template_tags[filter_name] = tag
        
        # Instead of calling create_card, implement the logic directly
        payload = {
            "name": name,
            "database_id": database_id,
            "display": display,
            "visualization_settings": visualization_settings or {},
            "dataset": False,
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": query,
                    "template-tags": template_tags
                }
            },
            "parameters": parameters
        }
        
        if description:
            payload["description"] = description
        if collection_id is not None:
            payload["collection_id"] = collection_id
            
        result = await metabase_client.request("POST", "/card", json=payload)
        return result
        
    except Exception as e:
        logger.error(f"Error in create_card_with_filters: {e}")
        raise


@mcp.tool
async def create_visualized_card(
    name: str,
    database_id: int,
    query: str,
    visualization_type: str,
    visualization_config: dict[str, Any],
    description: str | None = None,
    collection_id: int | None = None,
    filters: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create a card with specific visualization type and configuration
    
    Args:
        name: Name of the card
        database_id: Database ID to query
        query: SQL query (can contain {{filter}} placeholders if filters provided)
        visualization_type: Type of visualization (bar, line, pie, table, scalar, etc.)
        visualization_config: Configuration specific to the visualization type
        description: Optional description
        collection_id: Collection to place the card in
        filters: Optional list of filter definitions (see create_card_with_filters)
        
    Visualization Config Examples:
        For bar/line/area charts:
            {
                "dimensions": ["month"],  # X-axis fields
                "metrics": ["revenue", "profit"],  # Y-axis fields
                "x_axis_title": "Month",
                "y_axis_title": "Amount ($)",
                "stacked": True  # For stacked charts
            }
            
        For pie charts:
            {
                "dimension": "category",  # Field for slices
                "metric": "sales",  # Field for values
                "show_legend": True,
                "percentages": True
            }
            
        For scalar (single number):
            {
                "field": "total_revenue",
                "prefix": "$",
                "suffix": "",
                "decimals": 2,
                "compact": True  # Shows as 1.2K instead of 1200
            }
            
        For tables:
            {
                "pivot_column": "category",  # Optional
                "cell_column": "amount",  # Optional
                "column_settings": {...}  # Optional per-column settings
            }
            
    Example:
        # Create a bar chart
        await create_visualized_card(
            name="Monthly Revenue",
            database_id=1,
            query="SELECT month, SUM(revenue) as total FROM sales GROUP BY month",
            visualization_type="bar",
            visualization_config={
                "dimensions": ["month"],
                "metrics": ["total"],
                "y_axis_title": "Revenue ($)"
            }
        )
    """
    try:
        # Build visualization settings based on type
        visualization_settings = {}
        
        if visualization_type in ["bar", "line", "area"]:
            visualization_settings = create_graph_visualization(
                dimensions=visualization_config.get("dimensions", []),
                metrics=visualization_config.get("metrics", []),
                x_axis_title=visualization_config.get("x_axis_title"),
                y_axis_title=visualization_config.get("y_axis_title"),
                show_values=visualization_config.get("show_values", True),
                stacked=visualization_config.get("stacked", False),
                area=visualization_type == "area" or visualization_config.get("area", False)
            )
        elif visualization_type == "pie":
            visualization_settings = create_pie_visualization(
                dimension=visualization_config["dimension"],
                metric=visualization_config["metric"],
                show_legend=visualization_config.get("show_legend", True),
                show_total=visualization_config.get("show_total", True),
                percentages=visualization_config.get("percentages", True)
            )
        elif visualization_type in ["scalar", "smartscalar"]:
            visualization_settings = create_scalar_visualization(
                field=visualization_config["field"],
                prefix=visualization_config.get("prefix"),
                suffix=visualization_config.get("suffix"),
                decimals=visualization_config.get("decimals"),
                multiply_by=visualization_config.get("multiply_by"),
                compact=visualization_config.get("compact", False)
            )
        elif visualization_type == "gauge":
            visualization_settings = create_gauge_visualization(
                field=visualization_config["field"],
                min_value=visualization_config.get("min_value", 0),
                max_value=visualization_config.get("max_value", 100),
                segments=visualization_config.get("segments")
            )
        elif visualization_type == "table":
            visualization_settings = create_table_visualization(
                pivot_column=visualization_config.get("pivot_column"),
                cell_column=visualization_config.get("cell_column"),
                column_settings=visualization_config.get("column_settings"),
                table_columns=visualization_config.get("table_columns")
            )
        else:
            # For other types, use the config directly
            visualization_settings = visualization_config
            
        # If filters are provided, use create_card_with_filters
        if filters:
            return await create_card_with_filters(
                name=name,
                database_id=database_id,
                query=query,
                filters=filters,
                description=description,
                collection_id=collection_id,
                visualization_settings=visualization_settings,
                display=visualization_type
            )
        else:
            # Otherwise use create_card directly
            return await create_card(
                name=name,
                database_id=database_id,
                query=query,
                description=description,
                collection_id=collection_id,
                visualization_settings=visualization_settings,
                display=visualization_type
            )
            
    except Exception as e:
        logger.error(f"Error creating visualized card: {e}")
        raise


@mcp.tool
async def delete_card(card_id: int) -> dict[str, Any]:
    """Delete a card/question (hard delete)
    
    Note: This permanently deletes the card. To archive it, use update_card with archived=True
    
    Args:
        card_id: The ID of the card to delete
    """
    try:
        await metabase_client.request("DELETE", f"/card/{card_id}")
        return {"success": True, "message": f"Card {card_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting card {card_id}: {e}")
        raise


@mcp.tool
async def create_card_public_link(card_id: int) -> dict[str, Any]:
    """Generate a publicly-accessible link for a card
    
    Args:
        card_id: The ID of the card
    """
    try:
        result = await metabase_client.request("POST", f"/card/{card_id}/public_link")
        return result
    except Exception as e:
        logger.error(f"Error creating public link for card {card_id}: {e}")
        raise


@mcp.tool
async def delete_card_public_link(card_id: int) -> dict[str, Any]:
    """Delete the publicly-accessible link for a card
    
    Args:
        card_id: The ID of the card
    """
    try:
        await metabase_client.request("DELETE", f"/card/{card_id}/public_link")
        return {"success": True, "message": f"Public link for card {card_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting public link for card {card_id}: {e}")
        raise


@mcp.tool
async def create_dashboard_public_link(dashboard_id: int) -> dict[str, Any]:
    """Generate a publicly-accessible link for a dashboard
    
    Args:
        dashboard_id: The ID of the dashboard
    """
    try:
        result = await metabase_client.request("POST", f"/dashboard/{dashboard_id}/public_link")
        return result
    except Exception as e:
        logger.error(f"Error creating public link for dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def delete_dashboard_public_link(dashboard_id: int) -> dict[str, Any]:
    """Delete the publicly-accessible link for a dashboard
    
    Args:
        dashboard_id: The ID of the dashboard
    """
    try:
        await metabase_client.request("DELETE", f"/dashboard/{dashboard_id}/public_link")
        return {"success": True, "message": f"Public link for dashboard {dashboard_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting public link for dashboard {dashboard_id}: {e}")
        raise


@mcp.tool
async def get_table_fields(table_id: int, limit: int = 20) -> dict[str, Any]:
    """Get all fields/columns in a table
    
    Args:
        table_id: The ID of the table
        limit: Maximum number of fields to return (default: 20)
    """
    try:
        result = await metabase_client.request("GET", f"/table/{table_id}/query_metadata")
        
        # Apply field limiting if limit > 0 and there are more fields than the limit
        if limit > 0 and "fields" in result and len(result["fields"]) > limit:
            total_fields = len(result["fields"])
            result["fields"] = result["fields"][:limit]
            result["_truncated"] = True
            result["_total_fields"] = total_fields
            result["_limit_applied"] = limit
        
        return result
    except Exception as e:
        logger.error(f"Error getting table fields for table {table_id}: {e}")
        raise


# Cleanup handler
async def cleanup():
    """Clean up resources on shutdown"""
    await metabase_client.close()


def main():
    """Main entry point for the server"""
    try:
        # Support multiple transport methods
        import sys

        # Get host and port from environment variables
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))

        # Check for transport argument
        transport = "stdio"  # default
        if "--sse" in sys.argv:
            transport = "sse"
        elif "--http" in sys.argv:
            transport = "streamable-http"
        elif "--stdio" in sys.argv:
            transport = "stdio"

        logger.info(f"Starting Metabase MCP server with {transport} transport")

        if transport in ["sse", "streamable-http"]:
            logger.info(f"Server will be available at http://{host}:{port}")
            mcp.run(transport=transport, host=host, port=port)
        else:
            mcp.run(transport=transport)

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
