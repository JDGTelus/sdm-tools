"""Sprint database functionality."""

import json
import sqlite3
from rich.console import Console
from .core import execute_sql, backup_table, create_table
from ..config import DB_NAME, TABLE_NAME

console = Console()


def extract_sprint_data_from_issues():
    """Extract unique sprint data from the customfield_10020 field in issues table."""
    sprints = {}

    with sqlite3.connect(DB_NAME) as conn:
        # Check if the issues table exists
        cursor = execute_sql(
            conn,
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'",
        )
        if not cursor.fetchone():
            console.print(
                f"[bold red]Issues table '{TABLE_NAME}' does not exist. Please fetch Jira issues first.[/bold red]"
            )
            return {}

        # Check if customfield_10020 column exists
        cursor = execute_sql(conn, f"PRAGMA table_info({TABLE_NAME})")
        columns = [info[1] for info in cursor.fetchall()]
        if "customfield_10020" not in columns:
            console.print(
                "[bold red]customfield_10020 column not found in issues table. Sprint data not available.[/bold red]"
            )
            return {}

        # Fetch all sprint data from issues
        cursor = execute_sql(
            conn,
            f"SELECT customfield_10020 FROM {TABLE_NAME} WHERE customfield_10020 IS NOT NULL AND customfield_10020 != ''",
        )

        for row in cursor.fetchall():
            sprint_json = row[0]
            if not sprint_json:
                continue

            try:
                # The sprint data is stored as Python dict representation, not JSON
                # First try to parse as JSON, if that fails, use eval (safely)
                try:
                    sprint_list = json.loads(sprint_json)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to evaluate as Python literal
                    import ast

                    sprint_list = ast.literal_eval(sprint_json)

                # Handle both single sprint and multiple sprints
                if isinstance(sprint_list, list):
                    for sprint in sprint_list:
                        if isinstance(sprint, dict) and "id" in sprint:
                            sprint_id = str(sprint["id"])
                            # Store unique sprints by ID
                            if sprint_id not in sprints:
                                sprints[sprint_id] = sprint
                elif isinstance(sprint_list, dict) and "id" in sprint_list:
                    # Single sprint object
                    sprint_id = str(sprint_list["id"])
                    if sprint_id not in sprints:
                        sprints[sprint_id] = sprint_list

            except (
                json.JSONDecodeError,
                ValueError,
                SyntaxError,
                TypeError,
                KeyError,
            ) as e:
                console.print(
                    f"[bold yellow]Warning: Could not parse sprint data: {sprint_json[:100]}... Error: {e}[/bold yellow]"
                )
                continue

    return sprints


def create_sprints_table(sprints_data):
    """Create and populate the sprints table with unique sprint data."""
    if not sprints_data:
        console.print(
            "[bold yellow]No sprint data found to create table.[/bold yellow]"
        )
        return False

    sprint_table_name = f"{TABLE_NAME}_sprints"

    with sqlite3.connect(DB_NAME) as conn:
        # Check if sprints table already exists and back it up
        cursor = execute_sql(
            conn,
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{sprint_table_name}'",
        )
        if cursor.fetchone():
            backup_table(conn, sprint_table_name)

        # Get all possible fields from sprint data
        all_fields = set()
        for sprint in sprints_data.values():
            all_fields.update(sprint.keys())

        # Remove 'id' as it will be the primary key
        all_fields.discard("id")

        # Create the sprints table
        create_table(conn, sprint_table_name, all_fields)

        # Insert sprint data
        for sprint_id, sprint in sprints_data.items():
            # Prepare values for insertion
            fields_list = list(all_fields)
            values = [sprint_id] + [str(sprint.get(field, "")) for field in fields_list]

            # Create the INSERT query
            placeholders = ", ".join(["?"] * len(fields_list))
            fields_str = ", ".join(fields_list)

            execute_sql(
                conn,
                f"""
                INSERT OR REPLACE INTO {sprint_table_name} (id, {fields_str})
                VALUES (?, {placeholders})
            """,
                values,
            )

    console.print(
        f"[bold green]Created sprints table '{sprint_table_name}' with {len(sprints_data)} unique sprints.[/bold green]"
    )
    return True


def display_sprints_table():
    """Display the sprints table data."""
    sprint_table_name = f"{TABLE_NAME}_sprints"

    with sqlite3.connect(DB_NAME) as conn:
        # Check if sprints table exists
        cursor = execute_sql(
            conn,
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{sprint_table_name}'",
        )
        if not cursor.fetchone():
            console.print(
                f"[bold red]Sprints table '{sprint_table_name}' does not exist. Please create it first by fetching Jira issues.[/bold red]"
            )
            return

        # Get table info to determine columns
        cursor = execute_sql(conn, f"PRAGMA table_info({sprint_table_name})")
        columns = [info[1] for info in cursor.fetchall()]

        # Display key columns: id, name, state, startDate, endDate
        display_columns = ["id", "name", "state", "startDate", "endDate"]
        # Only include columns that exist in the table
        display_columns = [col for col in display_columns if col in columns]

        if not display_columns:
            console.print(
                "[bold red]No recognizable sprint columns found in table.[/bold red]"
            )
            return

        # Import display function from issues module
        from .issues import display_table_data

        display_table_data(conn, sprint_table_name, display_columns)


def process_sprints_from_issues():
    """Main function to extract and store sprint data from issues."""
    console.print("[bold yellow]Extracting sprint data from issues...[/bold yellow]")

    # Extract sprint data
    sprints_data = extract_sprint_data_from_issues()

    if not sprints_data:
        console.print("[bold red]No sprint data found in issues.[/bold red]")
        return False

    console.print(f"[bold cyan]Found {len(sprints_data)} unique sprints.[/bold cyan]")

    # Create sprints table
    success = create_sprints_table(sprints_data)

    if success:
        console.print(
            "[bold green]Sprint data processing completed successfully.[/bold green]"
        )

        # Ask if user wants to display the sprints table
        display_choice = (
            console.input(
                "[bold yellow]Do you want to display the sprints table? (y/N): [/bold yellow]"
            )
            .strip()
            .lower()
        )

        if display_choice in ["y", "yes"]:
            display_sprints_table()

    return success
