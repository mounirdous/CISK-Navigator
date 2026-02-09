# 🕸️ CISK Navigator

Interactive visualization tool for exploring relationships between **Challenges**, **Initiatives**, **Systems**, and **KPIs**.

![Version](https://img.shields.io/badge/version-2.7.5-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

- **🎯 Multi-Link Support**: Initiatives can address multiple challenges, systems support multiple initiatives
- **⭐ Priority Levels**: Visual priority indicators (⭐⭐⭐, ⭐⭐, ⭐)
- **🎚️ Weighted Relationships**: All links have weights (1-10)
- **💥 Impact Indicators**: High/Medium/Low impact badges
- **🎨 Custom Colors**: Configure colors for challenges, initiatives, systems, and KPIs in YAML
- **📊 Three Views**: Column view, interactive graph view, and Flow view (Sankey diagram)
- **🌊 Flow Visualization**: Sankey diagram with weight-based flow thickness showing relationship strength
- **📱 Mobile Touch Support**: Pinch-to-zoom, pan, and tap on mobile devices (iPhone, Android)
- **🔄 Season Filtering**: Filter by S1, S2, S3
- **📤 Upload & Download**: Upload YAML, download standalone HTML
- **📊 Analytics Support**: Add Google Analytics or any tracking code to generated HTML

## 🚀 Quick Start

### Use Online (No Installation)

Visit: **[Your Railway URL here after deployment]**

1. Upload your YAML file
2. Explore in column or graph view
3. Download standalone HTML

### Run Locally

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/CISK-Navigator.git
cd CISK-Navigator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py

# Open browser
open http://localhost:5002
```

## 🎨 Example Navigators

Try these fun example navigators with different themes and custom colors:

1. **🏃 Getting Fit** - Your personal health transformation journey
   - [YAML file](examples/getting_fit.yaml) | [Live HTML](examples/html/getting_fit.html)
   - Green/Orange/Red/Blue color scheme

2. **💰 Getting Rich** - Your wealth building roadmap
   - [YAML file](examples/getting_rich.yaml) | [Live HTML](examples/html/getting_rich.html)
   - Gold/Green/Blue/Purple color scheme

3. **📚 Staying Curious** - Your lifelong learning journey
   - [YAML file](examples/staying_curious.yaml) | [Live HTML](examples/html/staying_curious.html)
   - Pink/Purple/Teal/Amber color scheme

4. **💼 Finding Your Dream Job** - Career search navigator
   - [YAML file](examples/finding_job.yaml) | [Live HTML](examples/html/finding_job.html)
   - Red/Blue/Green/Yellow color scheme

Download any YAML file, customize it for your needs, and upload to create your own navigator!

## 📁 YAML Format

```yaml
meta:
  title: "Your Navigator Title"    # Required - displayed in generated HTML
  version: "1.0"                    # Optional - defaults to "1.0"
  colors:                           # Optional - customize visualization colors
    challenge: '#f0d24f'            # Default: yellow
    initiative: '#8fd0ff'           # Default: light blue
    system: '#1d4ed8'               # Default: blue
    kpi: '#22c55e'                  # Default: green

challenge_groups:
  - id: C1
    number: 1
    title: "Digital Transformation"
    priority: 1  # 1=⭐⭐⭐, 2=⭐⭐, 3=⭐

sub_challenges:
  - id: C1.SC1
    group_id: C1
    text: "Challenge description"
    priority: 1

initiatives:
  - id: I1
    season: S1
    text: "Initiative description"
    challenges:
      - challenge_id: C1.SC1
        weight: 10      # 1-10
        impact: H       # H/M/L
      - challenge_id: C1.SC2
        weight: 8
        impact: M

systems:
  - id: S1
    text: "System description"
    initiatives:
      - initiative_id: I1
        weight: 10
      - initiative_id: I2
        weight: 9

kpis:
  - id: K1
    text: "KPI description"
    systems:
      - system_id: S1
        weight: 9
      - system_id: S2
        weight: 10
```

## 📊 Views

### Column View
- 4-column responsive layout
- Priority stars and impact badges
- Weight indicators
- Season filtering
- Search functionality

### Graph View
- Vertical flow (Groups → Challenges → Initiatives → Systems → KPIs)
- Click/tap nodes to filter
- Back button navigation
- Full chain tracing
- Desktop: Drag, pan, mouse wheel zoom, zoom buttons
- Mobile: Pinch-to-zoom, pan with one finger, tap to select

### Flow View (Sankey Diagram)
- Visualize relationship strength through flow thickness
- 5 columns: Groups → Sub-Challenges → Initiatives → Systems → KPIs
- Weight-based flow lines (thicker = stronger relationship)
- Color-coded by entity type
- Click nodes to filter
- Synchronized with Graph and Column views

## 🌐 Deploy Your Own

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide to:
- Railway.app (recommended, free tier)
- Render.com (free tier)
- Vercel/Netlify (free)
- Heroku ($5-7/month)

Quick deploy to Railway:
1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. Deploy from GitHub repo
4. Done!

## 🛠️ Technology

- **Backend**: Python 3.11, Flask, PyYAML
- **Frontend**: Vanilla JavaScript, HTML5 Canvas
- **Deployment**: Gunicorn
- **Visualization**: Custom canvas-based graph

## 📖 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide for all platforms
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture and code structure
- Sample data: `data/full_sample_enhanced.yaml`
- Fun examples: See [🎨 Example Navigators](#-example-navigators) above

## 💡 Use Cases

- Digital transformation programs
- Enterprise architecture mapping
- Portfolio management
- Product roadmaps
- Strategic planning
- Technology governance

## 🤝 Contributing

Contributions welcome! Fork, modify, and submit pull requests.

## 📄 License

MIT License - Free for personal and commercial use

## 🙏 Credits

Built for strategic business planning and technology roadmap visualization.

---

**Version 2.7.5** - Enhanced with multi-links, priorities, weights, interactive graph view, Flow view (Sankey diagram), dual version display, analytics tracking, customizable colors, full mobile/desktop zoom support, and tooltips

### Recent Updates
- **v2.7.5** (Feb 2026): Graph and Flow view selections now sync back to Column view - full bidirectional sync
- **v2.7.4** (Feb 2026): Flow view uses gradient colors - flows transition from source color to target color
- **v2.7.3** (Feb 2026): Flow view shows selected node with visual highlight and selection indicator at top
- **v2.7.2** (Feb 2026): Column view selections now properly sync to Graph and Flow views
- **v2.7.1** (Feb 2026): Flow view selections sync to Graph view, filters persist when switching views
- **v2.7.0** (Feb 2026): Flow view redesigned with colored dots instead of boxes, cleaner look, dots are clickable with tooltips
- **v2.6.9** (Feb 2026): Flow view nodes maintain reasonable size (30-150px height) when filtered
- **v2.6.8** (Feb 2026): "Show All" button resets all views, season filtering now applies to Flow view
- **v2.6.7** (Feb 2026): Flow view expanded clickable area to include text labels, hover highlights, tooltips
- **v2.6.6** (Feb 2026): Flow view filtered layout uses full canvas space, all node types clickable
- **v2.6.5** (Feb 2026): Fix challenge group links in Flow view (use groupId instead of group_id)
- **v2.6.4** (Feb 2026): Fix Flow view link ID handling for all node types, enable clicking all nodes
- **v2.6.3** (Feb 2026): Fix challenge group filtering in Flow view, improve debug logging
- **v2.6.2** (Feb 2026): Fix Graph view link preservation when switching between views
- **v2.6.1** (Feb 2026): Fix Flow view sync with Graph view selections
- **v2.6.0** (Feb 2026): Flow View (Sankey diagram) with weight-based flow thickness, synchronized filtering across all views, clickable nodes
- **v2.5.3** (Feb 2026): Tooltip on hover to display full node names in graph view
- **v2.5.2** (Feb 2026): Enable mouse wheel zoom on desktop (scroll to zoom towards cursor)
- **v2.5.1** (Feb 2026): Mobile touch support - pinch-to-zoom and pan gestures on iPhone/Android
- **v2.5.0** (Feb 2026): Customizable colors for challenges, initiatives, systems, and KPIs via YAML configuration
- **v2.4.0** (Feb 2026): Analytics tracking support (Google Analytics, Plausible, etc.)
- **v2.3.3** (Feb 2026): Fixed graph navigation A→B→A scenario
- **v2.3.1** (Feb 2026): Upload page documentation, optional YAML version field
- **v2.3.0** (Feb 2026): Dual version display (app + data), customizable YAML title
