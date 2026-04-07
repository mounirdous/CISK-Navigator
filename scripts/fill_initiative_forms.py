"""Fill in missing initiative form fields for People & Transition Readiness space."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from app import create_app
from app.extensions import db
from app.models import Initiative
app = create_app()
ORG_ID = 24

FORMS = {
    "Assess business-facing and service ownership role fit": {
        "team": "CIO, HR Business Partner, Division IT leads, Business relationship managers",
        "deliverables": "- Person-to-role fit matrix for all business-facing IT roles\n- Fit score (1-3) per role with rationale\n- Development plan for partial-fit candidates\n- Sourcing recommendation for gap roles\n- Timeline for filling critical vacancies",
        "timeline": "May - June 2026",
        "group_label": "People Fit",
    },
    "Assess application, architecture and data role fit": {
        "team": "CIO, IT Leadership Team, Current application/architecture leads, HR",
        "deliverables": "- Person-to-role fit matrix for application, architecture, and data roles\n- Domain ownership map with named candidates\n- Skill gap analysis (cloud, data, integration)\n- Development vs hire recommendation per role\n- JD drafts for external hire roles",
        "timeline": "May - June 2026",
        "group_label": "People Fit",
    },
    "Assess infrastructure, operations and security role fit": {
        "team": "CIO, Infrastructure leads, Security officer, Site IT coordinators, HR",
        "deliverables": "- Person-to-role fit matrix for infra, ops, and security roles\n- Site-by-site coverage assessment\n- Critical single-person dependency list\n- Nearshore viability per role\n- Security role gap severity assessment",
        "timeline": "May - June 2026",
        "group_label": "People Fit",
    },
    "Assess governance, PMO and delivery role fit": {
        "team": "CIO, Current PMO/project managers, Finance controller, HR",
        "deliverables": "- Person-to-role fit matrix for governance and delivery roles\n- PMO model recommendation (dedicated vs shared)\n- Change management capability assessment\n- Vendor management role assessment\n- Portfolio management readiness view",
        "timeline": "May - June 2026",
        "group_label": "People Fit",
    },
    "Map critical capability gaps and single-person dependencies": {
        "team": "CIO, IT Leadership Team, HR, Key technical experts",
        "deliverables": "- Prioritised capability gap register\n- Single-person dependency heat map\n- Risk severity per gap (1-3)\n- Mitigation plan per critical gap\n- Cross-training recommendations\n- Cost estimate for gap closure",
        "timeline": "May - June 2026",
        "group_label": "Capability",
    },
    "Define development and upskilling priorities": {
        "team": "CIO, HR Learning & Development, IT Leadership, Individual contributors",
        "deliverables": "- Individual development plans for all fit-score-2 people\n- Training budget and timeline\n- Certification paths identified\n- Coaching/mentoring pairings\n- Rotation opportunities mapped\n- HR sign-off on development approach",
        "timeline": "May - June 2026",
        "group_label": "Capability",
    },
    "Define transition waves and sequencing logic": {
        "team": "CIO, HR, IT Leadership, Transformation PMO",
        "deliverables": "- Wave definition document (Wave 1-4 with triggers)\n- Dependency map between role changes\n- Alignment with SAP/transformation milestones\n- Rollback considerations per wave\n- Resource loading view\n- Go/no-go criteria per wave",
        "timeline": "June 2026",
        "group_label": "Transition",
    },
    "Plan stakeholder communication and change support": {
        "team": "CIO, HR Business Partner, Communications, IT Leadership",
        "deliverables": "- Communication plan with timeline\n- 1:1 conversation scripts per impact type\n- FAQ document for affected individuals\n- Town-hall preparation materials\n- Feedback channel setup\n- HR co-ownership agreement\n- Manager briefing pack",
        "timeline": "June 2026",
        "group_label": "Transition",
    },
    "Determine sourcing path per role cluster": {
        "team": "CIO, CFO, HR, IT Leadership, Procurement",
        "deliverables": "- Sourcing decision register (per role: develop/hire/nearshore/outsource/partner)\n- Rationale document per decision\n- Cost comparison across sourcing paths\n- JD drafts for external hire roles\n- Budget request for external hires\n- Board presentation on sourcing strategy",
        "timeline": "May - June 2026",
        "group_label": "Sourcing",
    },
    "Assess Lithuania nearshoring feasibility": {
        "team": "CIO, Kaunas site leadership, HR (local + group), IT Leadership",
        "deliverables": "- Lithuania IT talent market assessment\n- Role-by-role nearshoring viability matrix\n- Cost-benefit analysis (salary, overhead, travel)\n- Language and timezone fit assessment\n- Management model for remote IT team\n- Site leadership endorsement\n- Pilot role recommendations",
        "timeline": "May - June 2026",
        "group_label": "Sourcing",
    },
    "Evaluate outsourcing readiness and minimum scale": {
        "team": "CIO, CFO, Procurement, IT Leadership, Current ops leads",
        "deliverables": "- Service tower assessment matrix\n- Volume and complexity analysis per tower\n- Minimum viable scale thresholds\n- Vendor market scan (3-5 vendors per tower)\n- Cost-benefit comparison: outsource vs in-house vs hybrid\n- Risk assessment per tower\n- Recommendation: outsource / defer / hybrid per tower",
        "timeline": "May - June 2026",
        "group_label": "Sourcing",
    },
}

with app.app_context():
    updated = 0
    for ini in Initiative.query.filter_by(organization_id=ORG_ID).all():
        form_data = FORMS.get(ini.name)
        if form_data:
            for field, value in form_data.items():
                if not getattr(ini, field, None):
                    setattr(ini, field, value)
            updated += 1
            print(f"  Filled: {ini.name[:50]}")
        else:
            # Check if already has data
            empty = [f for f in ['team', 'deliverables', 'timeline', 'group_label'] if not getattr(ini, f, None)]
            if empty:
                print(f"  SKIPPED (no template): {ini.name[:50]} missing {empty}")

    db.session.commit()
    print(f"\nUpdated {updated} initiative forms")
