"""Generate standalone HTML reports with inlined data and styles."""

import os
import json
import re
from pathlib import Path
from rich.console import Console

console = Console()


def generate_standalone_report(report_name=None):
    """
    Generate standalone HTML report(s) in dist/ directory.
    
    Args:
        report_name: Specific report HTML filename (e.g., 'daily-activity-dashboard.html')
                    If None, generates standalone versions of ALL reports in ux/web/
    
    Process:
        1. Discover HTML files in ux/web/
        2. For each HTML file:
           a. Read the HTML template
           b. Inline CSS from shared-dashboard-styles.css
           c. Detect and inline JSON data file references (e.g., './data/*.json')
           d. Generate standalone version in dist/ with same filename
        3. Keep CDN scripts as-is (require network for React, Chart.js, etc.)
    
    Returns:
        List of generated file paths or None on error
    """
    try:
        # Define paths
        ux_web_dir = Path("ux/web")
        dist_dir = Path("dist")
        css_file = ux_web_dir / "shared-dashboard-styles.css"
        data_dir = ux_web_dir / "data"
        
        # Ensure dist directory exists
        dist_dir.mkdir(exist_ok=True)
        console.print(f"[dim]✓ Ensured dist/ directory exists[/dim]")
        
        # Find HTML files to process
        if report_name:
            html_files = [ux_web_dir / report_name]
            if not html_files[0].exists():
                console.print(f"[bold red]Error: {report_name} not found in ux/web/[/bold red]")
                return None
        else:
            html_files = list(ux_web_dir.glob("*.html"))
        
        if not html_files:
            console.print("[bold yellow]No HTML files found in ux/web/[/bold yellow]")
            return None
        
        console.print(f"[bold cyan]Found {len(html_files)} report(s) to process[/bold cyan]")
        
        # Read CSS content once
        css_content = ""
        if css_file.exists():
            with open(css_file, 'r') as f:
                css_content = f.read()
            console.print(f"[dim]✓ Loaded shared CSS ({len(css_content)} bytes)[/dim]")
        else:
            console.print("[bold yellow]Warning: shared-dashboard-styles.css not found[/bold yellow]")
        
        generated_files = []
        
        # Process each HTML file
        for html_file in html_files:
            console.print(f"\n[bold yellow]Processing: {html_file.name}[/bold yellow]")
            
            # Read HTML content
            with open(html_file, 'r') as f:
                html_content = f.read()
            
            # Step 1: Inline CSS
            html_content = _inline_css(html_content, css_content)
            console.print(f"[dim]  ✓ Inlined CSS styles[/dim]")
            
            # Step 2: Detect and inline JSON data
            html_content = _inline_json_data(html_content, data_dir)
            console.print(f"[dim]  ✓ Inlined JSON data[/dim]")
            
            # Step 3: Add note about CDN dependencies
            html_content = _add_network_note(html_content)
            console.print(f"[dim]  ✓ Added network requirement note[/dim]")
            
            # Write standalone file
            output_file = dist_dir / html_file.name
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            generated_files.append(str(output_file))
            console.print(f"[bold green]  ✓ Generated: {output_file}[/bold green]")
        
        return generated_files
        
    except Exception as e:
        console.print(f"[bold red]Error generating standalone report: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return None


def _inline_css(html_content, css_content):
    """Replace CSS link with inline styles."""
    # Pattern to match: <link rel="stylesheet" href="shared-dashboard-styles.css">
    css_link_pattern = r'<link\s+rel="stylesheet"\s+href="shared-dashboard-styles\.css"\s*/?>'
    
    # Create inline style tag
    inline_css = f'<style>\n/* Inlined from shared-dashboard-styles.css */\n{css_content}\n    </style>'
    
    # Replace the link tag
    html_content = re.sub(css_link_pattern, inline_css, html_content, flags=re.IGNORECASE)
    
    return html_content


def _inline_json_data(html_content, data_dir):
    """Detect fetch() calls and inline JSON data."""
    # Pattern to match: fetch("./data/FILENAME.json")
    fetch_pattern = r'fetch\("\.\/data\/([^"]+\.json)"\)'
    
    # Find all JSON files being fetched
    matches = list(re.finditer(fetch_pattern, html_content))
    
    for match in matches:
        json_filename = match.group(1)
        json_path = data_dir / json_filename
        
        if json_path.exists():
            # Read JSON data
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # Convert to JavaScript object string (compact for single line)
            json_str = json.dumps(json_data)
            
            # Pattern to replace the entire fetch().then().then() chain
            # Match: fetch("./data/FILE.json")\n.then((res) => res.json())\n.then((reportData) => {
            # Replace with: Promise.resolve(DATA).then((reportData) => {
            
            # Build pattern that handles newlines and whitespace
            old_pattern = (
                rf'fetch\("\.\/data\/{re.escape(json_filename)}"\)\s*'
                r'\.then\(\s*\([^)]+\)\s*=>\s*[^)]+\.json\(\)\s*\)\s*'
                r'\.then\(\s*\((\w+)\)\s*=>\s*\{'
            )
            
            new_code = (
                f'/* Inlined data from ./data/{json_filename} */\n          '
                f'Promise.resolve({json_str})\n            .then((\\1) => {{'
            )
            
            html_content = re.sub(old_pattern, new_code, html_content, count=1, flags=re.MULTILINE | re.DOTALL)
            
            console.print(f"[dim]    → Inlined: {json_filename} ({len(json_str)} bytes)[/dim]")
        else:
            console.print(f"[bold yellow]    ⚠ Warning: {json_filename} not found in data/[/bold yellow]")
    
    return html_content


def _add_network_note(html_content):
    """Add HTML comment noting CDN dependency."""
    note = """<!--
    ═══════════════════════════════════════════════════════════════════════
    STANDALONE REPORT - Generated by SDM Tools
    ═══════════════════════════════════════════════════════════════════════
    
    This is a self-contained report with all data and styling inlined.
    
    ⚠️  NETWORK REQUIREMENT:
    This file still requires internet access to load external libraries:
      - React 18
      - React DOM 18
      - Babel Standalone
      - TailwindCSS
      - Chart.js 4.4.0
    
    These libraries are loaded from CDN for optimal performance.
    Open this file directly in your browser (file:// protocol supported).
    
    Generated: Standalone version from ux/web/
    ═══════════════════════════════════════════════════════════════════════
-->
"""
    
    # Insert after <!DOCTYPE html>
    html_content = html_content.replace('<!DOCTYPE html>', f'<!DOCTYPE html>\n{note}')
    
    return html_content


def generate_all_standalone_reports():
    """Convenience function to generate all standalone reports."""
    return generate_standalone_report(report_name=None)


# ============================================================================
# BUNDLED SPA GENERATION
# ============================================================================

def _load_json_data(filepath):
    """Load JSON data from file."""
    path = Path(filepath)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return json.load(f)


def _load_css_file(filepath):
    """Load CSS content from file."""
    path = Path(filepath)
    if not path.exists():
        return ""
    with open(path, 'r') as f:
        return f.read()


def _build_spa_template(daily_data, sprint_data, css_content):
    """Build complete SPA HTML template with sidebar navigation."""
    from .spa_components import COMPONENT_CODE
    
    # Convert data to JS objects
    daily_js = json.dumps(daily_data, indent=2)
    sprint_js = json.dumps(sprint_data, indent=2)
    
    # Read the template file
    template_path = Path(__file__).parent / "spa_bundle_template.html"
    with open(template_path, 'r') as f:
        template = f.read()
    
    # Replace placeholders
    template = template.replace('/*{CSS_PLACEHOLDER}*/', css_content)
    template = template.replace('/*{DAILY_DATA_PLACEHOLDER}*/', daily_js)
    template = template.replace('/*{SPRINT_DATA_PLACEHOLDER}*/', sprint_js)
    template = template.replace('/*{COMPONENT_CODE_PLACEHOLDER}*/', COMPONENT_CODE)
    
    return template


def generate_bundle_spa(output_file=None):
    """
    Generate bundled SPA with all reports and side navigation.
    
    Creates a single standalone HTML file that includes:
    - Side navigation menu
    - Daily activity dashboard
    - Sprint activity dashboard
    - All data embedded inline
    - All styles embedded inline
    
    Args:
        output_file: Output file path (default: dist/reports-bundle.html)
    
    Returns:
        Path to generated file or None on error
    """
    if output_file is None:
        output_file = "dist/reports-bundle.html"
    
    console.print("\n[bold cyan]Generating Bundled SPA Report...[/bold cyan]")
    
    try:
        # 1. Load data files
        daily_data = _load_json_data("ux/web/data/daily_activity_report.json")
        sprint_data = _load_json_data("ux/web/data/sprint_activity_report.json")
        
        if not daily_data:
            console.print("[bold red]Error: daily_activity_report.json not found[/bold red]")
            console.print("[dim]Run 'Generate Reports > Single day report' first[/dim]")
            return None
        
        if not sprint_data:
            console.print("[bold red]Error: sprint_activity_report.json not found[/bold red]")
            console.print("[dim]Run 'Generate Reports > Full sprint report' first[/dim]")
            return None
        
        # 2. Load CSS
        css_content = _load_css_file("ux/web/shared-dashboard-styles.css")
        
        # 3. Build HTML template
        html_content = _build_spa_template(daily_data, sprint_data, css_content)
        
        # 4. Write to dist/
        Path("dist").mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        # Calculate sizes
        daily_size = len(json.dumps(daily_data))
        sprint_size = len(json.dumps(sprint_data))
        total_size = len(html_content)
        
        console.print(f"[bold green]✓ Bundled SPA generated: {output_file}[/bold green]")
        console.print(f"[dim]  Daily data: {daily_size:,} bytes[/dim]")
        console.print(f"[dim]  Sprint data: {sprint_size:,} bytes[/dim]")
        console.print(f"[dim]  Total file size: {total_size:,} bytes ({total_size/1024:.1f} KB)[/dim]")
        
        return output_file
        
    except Exception as e:
        console.print(f"[bold red]Error generating bundled SPA: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return None
