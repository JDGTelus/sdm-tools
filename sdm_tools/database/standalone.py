"""Generate standalone HTML reports with inlined data and styles."""

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
        console.print("[dim]✓ Ensured dist/ directory exists[/dim]")

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
            with open(css_file) as f:
                css_content = f.read()
            console.print(f"[dim]✓ Loaded shared CSS ({len(css_content)} bytes)[/dim]")
        else:
            console.print(
                "[bold yellow]Warning: shared-dashboard-styles.css not found[/bold yellow]"
            )

        generated_files = []

        # Process each HTML file
        for html_file in html_files:
            console.print(f"\n[bold yellow]Processing: {html_file.name}[/bold yellow]")

            # Read HTML content
            with open(html_file) as f:
                html_content = f.read()

            # Step 1: Inline CSS
            html_content = _inline_css(html_content, css_content)
            console.print("[dim]  ✓ Inlined CSS styles[/dim]")

            # Step 2: Detect and inline JSON data
            html_content = _inline_json_data(html_content, data_dir)
            console.print("[dim]  ✓ Inlined JSON data[/dim]")

            # Step 3: Add note about CDN dependencies
            html_content = _add_network_note(html_content)
            console.print("[dim]  ✓ Added network requirement note[/dim]")

            # Write standalone file
            output_file = dist_dir / html_file.name
            with open(output_file, "w") as f:
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
    inline_css = (
        f"<style>\n/* Inlined from shared-dashboard-styles.css */\n{css_content}\n    </style>"
    )

    # Replace the link tag
    html_content = re.sub(css_link_pattern, inline_css, html_content, flags=re.IGNORECASE)

    return html_content


def _inline_json_data(html_content, data_dir):
    """Detect fetch() calls and inline JSON data."""
    # Pattern to match: fetch("./data/FILENAME.json") or fetch('./data/FILENAME.json')
    fetch_pattern = r'fetch\(["\']\.\/data\/([^"\']+\.json)["\']\)'

    # Find all JSON files being fetched
    matches = list(re.finditer(fetch_pattern, html_content))

    for match in matches:
        json_filename = match.group(1)
        json_path = data_dir / json_filename

        if json_path.exists():
            # Read JSON data
            with open(json_path) as f:
                json_data = json.load(f)

            # Convert to JavaScript object string (compact for single line)
            json_str = json.dumps(json_data)

            # Pattern to replace the entire fetch().then().then() chain
            # Handles multiple variations:
            # 1. Simple: fetch(...).then((res) => res.json()).then((data) => {
            # 2. With error check: fetch(...).then((res) => { if (!res.ok) ...; return res.json(); }).then((data) => {

            # First try the complex pattern (with error checking)
            complex_pattern = (
                rf'fetch\(["\']\.\/data\/{re.escape(json_filename)}["\']\)\s*'
                r"\.then\(\s*\(([^)]+)\)\s*=>\s*\{[^}]*?return\s+\1\.json\(\);?\s*\}\s*\)\s*"
                r"\.then\(\s*\((\w+)\)\s*=>\s*\{"
            )

            # Try complex pattern first
            match = re.search(complex_pattern, html_content, re.MULTILINE | re.DOTALL)

            if match:
                # Complex pattern matched
                new_code = (
                    f"/* Inlined data from ./data/{json_filename} */\n          "
                    f"Promise.resolve({json_str})\n            .then(({match.group(2)}) => {{"
                )
                html_content = re.sub(
                    complex_pattern, new_code, html_content, count=1, flags=re.MULTILINE | re.DOTALL
                )
            else:
                # Try simple pattern
                simple_pattern = (
                    rf'fetch\(["\']\.\/data\/{re.escape(json_filename)}["\']\)\s*'
                    r"\.then\(\s*\([^)]+\)\s*=>\s*[^.]+\.json\(\)\s*\)\s*"
                    r"\.then\(\s*\((\w+)\)\s*=>\s*\{"
                )
                new_code = (
                    f"/* Inlined data from ./data/{json_filename} */\n          "
                    f"Promise.resolve({json_str})\n            .then((\\1) => {{"
                )
                html_content = re.sub(
                    simple_pattern, new_code, html_content, count=1, flags=re.MULTILINE | re.DOTALL
                )

            console.print(f"[dim]    → Inlined: {json_filename} ({len(json_str)} bytes)[/dim]")
        else:
            console.print(
                f"[bold yellow]    ⚠ Warning: {json_filename} not found in data/[/bold yellow]"
            )

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
    html_content = html_content.replace("<!DOCTYPE html>", f"<!DOCTYPE html>\n{note}")

    return html_content


def generate_all_standalone_reports():
    """Convenience function to generate all standalone reports."""
    return generate_standalone_report(report_name=None)


# ==================================================
# BUNDLED SPA GENERATION
# ==================================================


def _discover_standalone_reports():
    """
    Discover all standalone HTML reports in dist/ directory.

    Returns:
        List of dicts with report metadata, sorted alphabetically by filename
    """
    import re

    dist_dir = Path("dist")
    if not dist_dir.exists():
        return []

    reports = []
    for html_file in sorted(dist_dir.glob("*.html")):
        # Skip the bundle itself
        if html_file.name == "reports-bundle.html":
            continue

        # Read file and extract metadata
        with open(html_file) as f:
            content = f.read()

        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", content)
        title = title_match.group(1) if title_match else html_file.stem.replace("-", " ").title()

        # Extract report type
        type_match = re.search(r'"report_type":\s*"(\w+)"', content)
        report_type = type_match.group(1) if type_match else "unknown"

        # Determine icon and view name based on filename/type
        if "daily" in html_file.name.lower() or report_type == "daily":
            icon = "📅"
            view_name = "daily"
        elif "velocity" in html_file.name.lower() or report_type == "sprint_velocity":
            icon = "📈"
            view_name = "velocity"
        elif "sprint" in html_file.name.lower() or report_type in ["multi_sprint", "sprint"]:
            icon = "📊"
            view_name = "sprint"
        else:
            icon = "📄"
            view_name = html_file.stem.replace("-", "_")

        reports.append(
            {
                "filename": html_file.name,
                "filepath": html_file,
                "title": title,
                "report_type": report_type,
                "icon": icon,
                "view_name": view_name,
                "size": html_file.stat().st_size,
            }
        )

    return reports


def _extract_data_from_standalone(filepath):
    """
    Extract embedded JSON data from a standalone HTML file.

    Args:
        filepath: Path to standalone HTML file

    Returns:
        Parsed JSON data object, or None if extraction fails
    """
    import re

    with open(filepath) as f:
        content = f.read()

    # Pattern: Promise.resolve({...data...}).then((reportData)
    pattern = r"Promise\.resolve\((.*?)\)\s*\.then\(\(reportData\)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        console.print(f"[yellow]Warning: Could not extract data from {filepath.name}[/yellow]")
        return None

    data_str = match.group(1)

    try:
        data = json.loads(data_str)
        return data
    except json.JSONDecodeError as e:
        console.print(f"[red]Error parsing JSON from {filepath.name}: {e}[/red]")
        return None


def _extract_component_from_standalone(filepath):
    """
    Extract React component code from a standalone HTML file.

    Args:
        filepath: Path to standalone HTML file

    Returns:
        Component JavaScript code as string, or None if extraction fails
    """
    import re

    with open(filepath) as f:
        content = f.read()

    # Pattern: <script type="text/babel">...component code...</script>
    pattern = r'<script type="text/babel">\s*(.*?)</script>'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        console.print(
            f"[yellow]Warning: Could not extract components from {filepath.name}[/yellow]"
        )
        return None

    component_code = match.group(1)

    # Remove the React hooks declaration (will be declared once in bundle)
    # Pattern: const { useState, useEffect, useRef } = React;
    react_hooks_pattern = (
        r"\s*const\s*\{\s*useState\s*,\s*useEffect\s*,?\s*useRef?\s*\}\s*=\s*React\s*;"
    )
    component_code = re.sub(react_hooks_pattern, "", component_code)

    # Remove the ReactDOM render calls at the end
    # Keep everything before ReactDOM.render or ReactDOM.createRoot
    render_patterns = [
        r"\s*//\s*Render.*?ReactDOM\.render\([^;]+\);",
        r"\s*//\s*Render.*?const root = ReactDOM\.createRoot.*?root\.render\([^;]+\);",
        r"\s*ReactDOM\.render\([^;]+\);",
        r"\s*const root = ReactDOM\.createRoot.*?root\.render\([^;]+\);",
    ]

    for pattern in render_patterns:
        component_code = re.sub(pattern, "", component_code, flags=re.DOTALL)

    return component_code.strip()


def _extract_css_from_standalone(filepath):
    """
    Extract inlined CSS from a standalone HTML file.

    Args:
        filepath: Path to standalone HTML file

    Returns:
        CSS content as string, or empty string if not found
    """
    import re

    with open(filepath) as f:
        content = f.read()

    # Extract ALL <style> blocks from the file (except TailwindCSS config)
    # Pattern: <style>...content...</style>
    pattern = r"<style>(.*?)</style>"
    matches = re.findall(pattern, content, re.DOTALL)

    css_blocks = []
    for css in matches:
        css = css.strip()
        # Skip TailwindCSS config blocks (they contain JavaScript)
        if "tailwind.config" in css or len(css) < 50:
            continue
        css_blocks.append(css)

    # Join all CSS blocks with newlines
    if css_blocks:
        return "\n\n".join(css_blocks)

    return ""


def generate_bundle_spa(output_file=None):
    """
    Generate bundled SPA from existing standalone reports in dist/.

    Discovers all standalone HTML files in dist/, extracts their data
    and components, and creates a unified SPA with dynamic navigation.
    First report found (alphabetically) becomes the default landing view.

    Args:
        output_file: Output file path (default: dist/reports-bundle.html)

    Returns:
        Path to generated file or None on error
    """

    if output_file is None:
        output_file = "dist/reports-bundle.html"

    console.print("\n[bold cyan]Generating Bundled SPA from Standalone Reports...[/bold cyan]")

    try:
        # Step 1: Discover standalone reports
        reports = _discover_standalone_reports()

        if not reports:
            console.print("[bold red]Error: No standalone reports found in dist/[/bold red]")
            console.print(
                "[dim]Run 'Generate Reports > Generate standalone report (dist/)' first[/dim]"
            )
            return None

        console.print(f"[dim]Found {len(reports)} standalone report(s):[/dim]")
        for i, report in enumerate(reports):
            default_marker = " [default]" if i == 0 else ""
            console.print(
                f"[dim]  {i+1}. {report['icon']} {report['title']} ({report['filename']}){default_marker}[/dim]"
            )

        # Step 2: Extract data from each report
        console.print("\n[dim]Extracting data from standalone files...[/dim]")
        reports_data = {}
        total_data_size = 0

        for report in reports:
            data = _extract_data_from_standalone(report["filepath"])

            if data:
                reports_data[report["view_name"]] = data
                data_size = len(json.dumps(data))
                total_data_size += data_size
                console.print(f"[dim]  ✓ {report['filename']}: {data_size:,} bytes[/dim]")
            else:
                console.print(f"[yellow]  ✗ {report['filename']}: no data extracted[/yellow]")

        if not reports_data:
            console.print("[bold red]Error: No data could be extracted from reports[/bold red]")
            return None

        # Step 3: Extract components from each report
        console.print("\n[dim]Extracting components from standalone files...[/dim]")
        all_components = []

        for report in reports:
            component_code = _extract_component_from_standalone(report["filepath"])

            if component_code:
                all_components.append(
                    f"\n      // ==================== {report['title']} ====================\n{component_code}\n"
                )
                console.print(f"[dim]  ✓ {report['filename']}: {len(component_code):,} chars[/dim]")
            else:
                console.print(f"[yellow]  ✗ {report['filename']}: no components extracted[/yellow]")

        # Step 4: Extract and merge CSS
        console.print("\n[dim]Extracting CSS from standalone files...[/dim]")
        all_css = []
        seen_css = set()

        for report in reports:
            css = _extract_css_from_standalone(report["filepath"])
            if css and css not in seen_css:
                all_css.append(css)
                seen_css.add(css)
                console.print(f"[dim]  ✓ {report['filename']}: {len(css):,} chars[/dim]")

        merged_css = "\n".join(all_css)

        # Step 5: Build reports metadata for sidebar
        reports_metadata = [
            {"view_name": r["view_name"], "title": r["title"], "icon": r["icon"]} for r in reports
        ]

        # Step 6: Build the bundle using new dynamic template approach
        console.print("\n[dim]Building bundle template...[/dim]")

        # Build data object JavaScript
        data_entries = []
        for view_name, data in reports_data.items():
            data_json = json.dumps(data, indent=2)
            # Indent the JSON properly
            indented_json = "\n".join("    " + line for line in data_json.split("\n"))
            data_entries.append(f"  '{view_name}':\n{indented_json}")

        embedded_data_js = "{\n" + ",\n".join(data_entries) + "\n  }"

        # Build metadata JavaScript array
        metadata_js = json.dumps(reports_metadata, indent=2)
        indented_metadata = "\n".join("        " + line for line in metadata_js.split("\n"))

        # Build component code
        all_components_code = "\n".join(all_components)

        # Create the complete bundle HTML
        bundle_html = _build_dynamic_bundle_template(
            embedded_data=embedded_data_js,
            reports_metadata=indented_metadata,
            components_code=all_components_code,
            css_content=merged_css,
            default_view=reports[0]["view_name"],  # First report is default
        )

        # Step 7: Write to dist/
        Path("dist").mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            f.write(bundle_html)

        # Calculate sizes
        total_size = len(bundle_html)

        console.print(f"\n[bold green]✓ Bundled SPA generated: {output_file}[/bold green]")
        console.print(f"[dim]  Reports included: {len(reports)}[/dim]")
        console.print(f"[dim]  Default landing: {reports[0]['icon']} {reports[0]['title']}[/dim]")
        console.print(f"[dim]  Total data size: {total_data_size:,} bytes[/dim]")
        console.print(
            f"[dim]  Total file size: {total_size:,} bytes ({total_size/1024:.1f} KB)[/dim]"
        )

        return output_file

    except Exception as e:
        console.print(f"[bold red]Error generating bundled SPA: {e}[/bold red]")
        import traceback

        traceback.print_exc()
        return None


def _build_dynamic_bundle_template(
    embedded_data, reports_metadata, components_code, css_content, default_view
):
    """
    Build the dynamic bundle HTML template.

    This creates a complete HTML file that doesn't rely on spa_components.py
    but instead uses extracted components from standalone files.
    """

    template = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SDM Tools - Reports Bundle</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
      tailwind.config = {{
        theme: {{
          extend: {{
            colors: {{
              "telus-purple": "#4B0082",
              "telus-green": "#66CC00",
              "telus-blue": "#0066CC",
              "telus-light-purple": "#8A2BE2",
              "telus-dark-purple": "#2E0054",
            }},
          }},
        }},
      }};
    </script>
    <style>
{css_content}

/* Sidebar navigation styles */
.sidebar {{
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  background: linear-gradient(180deg, #4B0082, #2E0054);
  transition: width 0.3s ease;
  z-index: 1000;
  overflow: hidden;
  box-shadow: 2px 0 10px rgba(0,0,0,0.1);
}}

.sidebar-open {{ width: 260px; }}
.sidebar-closed {{ width: 70px; }}

.sidebar-header {{
  padding: 20px;
  color: white;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  margin-bottom: 10px;
}}

.sidebar-title {{
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
}}

.toggle-btn {{
  position: absolute;
  top: 20px;
  right: 15px;
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  font-size: 16px;
}}

.toggle-btn:hover {{
  background: rgba(255,255,255,0.3);
}}

.nav-item {{
  padding: 16px 20px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
  overflow: hidden;
}}

.nav-item-icon {{
  font-size: 20px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}}

.nav-item-text {{
  font-size: 14px;
  font-weight: 500;
}}

.nav-item:hover {{
  background: rgba(255,255,255,0.1);
  padding-left: 24px;
}}

.nav-item.active {{
  background: rgba(255,255,255,0.2);
  border-left: 4px solid #66CC00;
  font-weight: 600;
}}

.sidebar-footer {{
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  color: rgba(255,255,255,0.6);
  font-size: 11px;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.1);
  white-space: nowrap;
  overflow: hidden;
}}

.main-content {{
  transition: margin-left 0.3s ease;
}}

.main-content.with-sidebar-open {{
  margin-left: 260px;
}}

.main-content.with-sidebar-closed {{
  margin-left: 70px;
}}
    </style>
  </head>
  <body class="bg-gray-50">
    <div id="root"></div>
    <script type="text/babel">
      const {{ useState, useEffect, useRef }} = React;

      // ═══════════════════════════════════════════════════════════════════════
      // EMBEDDED DATA FROM STANDALONE REPORTS
      // ═══════════════════════════════════════════════════════════════════════

      const EMBEDDED_DATA = {embedded_data};

      // ═══════════════════════════════════════════════════════════════════════
      // COMPONENTS EXTRACTED FROM STANDALONE REPORTS
      // ═══════════════════════════════════════════════════════════════════════
{components_code}

      // ═══════════════════════════════════════════════════════════════════════
      // SIDEBAR NAVIGATION
      // ═══════════════════════════════════════════════════════════════════════

      const Sidebar = ({{ currentView, onNavigate, isOpen, toggle, reports }}) => {{
        return (
          <div className={{`sidebar ${{isOpen ? 'sidebar-open' : 'sidebar-closed'}}`}}>
            <div className="sidebar-header">
              <div className="sidebar-title">
                {{isOpen ? 'SDM Reports' : 'SDM'}}
              </div>
              <button onClick={{toggle}} className="toggle-btn">
                {{isOpen ? '←' : '→'}}
              </button>
            </div>

            <nav>
              {{reports.map(report => (
                <div
                  key={{report.view_name}}
                  className={{`nav-item ${{currentView === report.view_name ? 'active' : ''}}`}}
                  onClick={{() => onNavigate(report.view_name)}}
                >
                  <span className="nav-item-icon">{{report.icon}}</span>
                  {{isOpen && <span className="nav-item-text">{{report.title}}</span>}}
                </div>
              ))}}
            </nav>

            {{isOpen && (
              <div className="sidebar-footer">
                SDM Tools<br/>Bundled Reports
              </div>
            )}}
          </div>
        );
      }};

      // ═══════════════════════════════════════════════════════════════════════
      // MAIN APP WITH DYNAMIC NAVIGATION
      // ═══════════════════════════════════════════════════════════════════════

      const BundledReportsApp = () => {{
        const reportsMetadata = {reports_metadata};

        const [currentView, setCurrentView] = useState('{default_view}');
        const [sidebarOpen, setSidebarOpen] = useState(true);

        // Render the appropriate dashboard based on current view
        const renderDashboard = () => {{
          if (currentView === 'daily' && EMBEDDED_DATA.daily) {{
            return <DailyActivityDashboard />;
          }} else if (currentView === 'sprint' && EMBEDDED_DATA.sprint) {{
            return <SprintActivityDashboard />;
          }} else if (currentView === 'velocity' && EMBEDDED_DATA.velocity) {{
            return <App />;
          }}
          return <div className="flex items-center justify-center h-screen">
            <div className="text-xl text-gray-600">No data available for this view</div>
          </div>;
        }};

        return (
          <>
            <Sidebar
              currentView={{currentView}}
              onNavigate={{setCurrentView}}
              isOpen={{sidebarOpen}}
              toggle={{() => setSidebarOpen(!sidebarOpen)}}
              reports={{reportsMetadata}}
            />
            <div className={{`main-content ${{sidebarOpen ? 'with-sidebar-open' : 'with-sidebar-closed'}}`}}>
              {{renderDashboard()}}
            </div>
          </>
        );
      }};

      // Render the app
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(<BundledReportsApp />);
    </script>
  </body>
</html>
"""

    return template
