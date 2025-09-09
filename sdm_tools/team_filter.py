"""
Team Member Extraction and Filtering Module
Extracts team members from Jira data and filters reports accordingly
"""
import sqlite3
import json
from typing import Set, Tuple, List
from .utils import console


class TeamMemberExtractor:
    def __init__(self, db_path="sdm_tools.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        self.conn.close()
    
    def extract_team_members(self) -> List[Tuple[str, str]]:
        """Extract team members from Jira assignee data"""
        query = "SELECT DISTINCT assignee FROM iotmi_3p_issues WHERE assignee IS NOT NULL AND assignee != 'null'"
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        
        team_members = []
        seen_emails = set()
        seen_names = set()
        
        for row in results:
            try:
                assignee_str = row['assignee']
                
                # Try JSON first
                try:
                    assignee_data = json.loads(assignee_str)
                except json.JSONDecodeError:
                    # If JSON fails, try eval (for Python dict strings)
                    try:
                        assignee_data = eval(assignee_str)
                    except:
                        console.print(f"[yellow]Warning: Could not parse assignee data: {assignee_str[:100]}...[/yellow]")
                        continue
                
                display_name = assignee_data.get('displayName', '').strip()
                email_address = assignee_data.get('emailAddress', '').strip()
                
                if display_name and display_name not in seen_names:
                    team_members.append((display_name, email_address))
                    seen_names.add(display_name)
                    if email_address:
                        seen_emails.add(email_address)
                        
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse assignee data: {e}[/yellow]")
                continue
        
        return team_members
    
    def get_team_emails(self) -> Set[str]:
        """Get set of team member email addresses"""
        team_members = self.extract_team_members()
        return {email for name, email in team_members if email}
    
    def get_team_names(self) -> Set[str]:
        """Get set of team member display names"""
        team_members = self.extract_team_members()
        return {name for name, email in team_members if name}
    
    def create_team_member_table(self):
        """Create a temporary table with team member information"""
        # Drop existing table if it exists
        self.conn.execute("DROP TABLE IF EXISTS team_members")
        
        # Create team members table
        create_table_sql = """
        CREATE TABLE team_members (
            display_name TEXT,
            email_address TEXT,
            PRIMARY KEY (display_name, email_address)
        )
        """
        self.conn.execute(create_table_sql)
        
        # Insert team members
        team_members = self.extract_team_members()
        for name, email in team_members:
            self.conn.execute(
                "INSERT OR IGNORE INTO team_members (display_name, email_address) VALUES (?, ?)",
                (name, email or '')
            )
        
        self.conn.commit()
        console.print(f"[green]✓ Created team_members table with {len(team_members)} members[/green]")
        
        return team_members
    
    def display_team_members(self):
        """Display the extracted team members"""
        team_members = self.extract_team_members()
        
        console.print(f"\n[bold cyan]📋 Team Members from Jira Tickets ({len(team_members)} total):[/bold cyan]")
        for i, (name, email) in enumerate(team_members, 1):
            email_display = email if email else "[dim]No email[/dim]"
            console.print(f"  {i:2d}. [cyan]{name}[/cyan] - {email_display}")
        
        return team_members


def get_team_filter_conditions() -> Tuple[str, str]:
    """Generate SQL conditions for filtering by team members"""
    extractor = TeamMemberExtractor()
    try:
        team_emails = extractor.get_team_emails()
        team_names = extractor.get_team_names()
        
        # Create email filter condition
        email_conditions = []
        if team_emails:
            email_list = "', '".join(team_emails)
            email_conditions.append(f"author_email IN ('{email_list}')")
            email_conditions.append(f"author IN ('{email_list}')")
        
        # Create name filter condition  
        name_conditions = []
        if team_names:
            name_list = "', '".join(team_names)
            name_conditions.append(f"author_name IN ('{name_list}')")
            name_conditions.append(f"author IN ('{name_list}')")
        
        # Combine conditions
        all_conditions = email_conditions + name_conditions
        filter_condition = " OR ".join(all_conditions) if all_conditions else "1=0"
        
        return filter_condition, f"Team filter: {len(team_emails)} emails, {len(team_names)} names"
        
    finally:
        extractor.close()


if __name__ == "__main__":
    extractor = TeamMemberExtractor()
    try:
        team_members = extractor.display_team_members()
        extractor.create_team_member_table()
        
        filter_condition, description = get_team_filter_conditions()
        console.print(f"\n[bold yellow]Filter Condition:[/bold yellow] {description}")
        
    finally:
        extractor.close()
