# 🕸️ CISK Navigator

Interactive visualization tool for exploring relationships between **Challenges**, **Initiatives**, **Systems**, and **KPIs**.

![Version](https://img.shields.io/badge/version-2.5.2-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

- **🎯 Multi-Link Support**: Initiatives can address multiple challenges, systems support multiple initiatives
- **⭐ Priority Levels**: Visual priority indicators (⭐⭐⭐, ⭐⭐, ⭐)
- **🎚️ Weighted Relationships**: All links have weights (1-10)
- **💥 Impact Indicators**: High/Medium/Low impact badges
- **🎨 Custom Colors**: Configure colors for challenges, initiatives, systems, and KPIs in YAML
- **📊 Two Views**: Column view and interactive graph view
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

**Version 2.5.2** - Enhanced with multi-links, priorities, weights, interactive graph view, dual version display, analytics tracking, customizable colors, and full mobile/desktop zoom support

### Recent Updates
- **v2.5.2** (Feb 2026): Enable mouse wheel zoom on desktop (scroll to zoom towards cursor)
- **v2.5.1** (Feb 2026): Mobile touch support - pinch-to-zoom and pan gestures on iPhone/Android
- **v2.5.0** (Feb 2026): Customizable colors for challenges, initiatives, systems, and KPIs via YAML configuration
- **v2.4.0** (Feb 2026): Analytics tracking support (Google Analytics, Plausible, etc.)
- **v2.3.3** (Feb 2026): Fixed graph navigation A→B→A scenario
- **v2.3.1** (Feb 2026): Upload page documentation, optional YAML version field
- **v2.3.0** (Feb 2026): Dual version display (app + data), customizable YAML title
