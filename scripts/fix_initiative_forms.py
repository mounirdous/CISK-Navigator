"""Fix initiative forms with correct field names and pipe format."""
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
        "responsible_person": "CIO",
        "team_members": "CIO + HR Business Partner + Division IT leads + Business relationship managers",
        "handover_organization": "IT Leadership + HR",
        "impact_rationale": "Business-facing roles are the primary interface between IT and the business. Without clear fit assessment, the new operating model risks starting with the wrong people in customer-facing positions, eroding trust built during onboarding.",
        "deliverables": "1 | Person-to-role fit matrix for all business-facing roles | Week 2\n2 | Fit score with rationale per role | Week 3\n3 | Development plan for partial-fit candidates | Week 4\n4 | Sourcing recommendation for gap roles | Week 5\n5 | Board-ready summary of business-facing role readiness | Week 6",
    },
    "Assess application, architecture and data role fit": {
        "responsible_person": "CIO",
        "team_members": "CIO + IT Leadership + Current application and architecture leads + HR",
        "handover_organization": "IT Leadership + CAB",
        "impact_rationale": "Application and architecture roles define the technical backbone of the future IT function. Gaps here directly delay SAP transformation, data governance, and integration modernisation.",
        "deliverables": "1 | Person-to-role fit matrix for app, arch, and data roles | Week 2\n2 | Domain ownership map with named candidates | Week 3\n3 | Skill gap analysis (cloud, data, integration) | Week 4\n4 | Development vs hire recommendation per role | Week 5\n5 | JD drafts for external hire roles | Week 6",
    },
    "Assess infrastructure, operations and security role fit": {
        "responsible_person": "CIO",
        "team_members": "CIO + Infrastructure leads + Security officer + Site IT coordinators + HR",
        "handover_organization": "IT Leadership + Sites",
        "impact_rationale": "Infrastructure and security roles underpin operational stability and compliance. Single-person dependencies in these areas create unacceptable business continuity risk.",
        "deliverables": "1 | Person-to-role fit matrix for infra, ops, and security | Week 2\n2 | Site-by-site coverage assessment | Week 3\n3 | Critical single-person dependency list | Week 4\n4 | Nearshore viability per role | Week 5\n5 | Security role gap severity assessment | Week 6",
    },
    "Assess governance, PMO and delivery role fit": {
        "responsible_person": "CIO",
        "team_members": "CIO + Current PMO and project managers + Finance controller + HR",
        "handover_organization": "IT Leadership + CFO",
        "impact_rationale": "Governance and delivery roles determine the organisation's ability to execute the transformation. Without PMO and change management capability, the SAP program and operating model redesign will lack execution discipline.",
        "deliverables": "1 | Person-to-role fit matrix for governance and delivery | Week 2\n2 | PMO model recommendation | Week 3\n3 | Change management capability assessment | Week 4\n4 | Vendor management role assessment | Week 5\n5 | Portfolio management readiness view | Week 6",
    },
    "Map critical capability gaps and single-person dependencies": {
        "responsible_person": "CIO",
        "team_members": "CIO + IT Leadership + HR + Key technical experts",
        "handover_organization": "HR + IT Leadership",
        "impact_rationale": "Capability gaps and single-person dependencies are the highest-risk items in the transition. Without a structured register, mitigation actions will be reactive rather than planned, increasing the chance of critical failures.",
        "deliverables": "1 | Prioritised capability gap register | Week 2\n2 | Single-person dependency heat map | Week 3\n3 | Risk severity rating per gap | Week 4\n4 | Mitigation plan per critical gap | Week 5\n5 | Cross-training recommendations | Week 5\n6 | Cost estimate for gap closure | Week 6",
    },
    "Define development and upskilling priorities": {
        "responsible_person": "CIO",
        "team_members": "CIO + HR Learning and Development + IT Leadership + Individual contributors",
        "handover_organization": "HR",
        "impact_rationale": "People with partial fit (score 2) are the most valuable investment targets. Structured development plans convert potential into readiness, reducing external hiring cost and preserving institutional knowledge.",
        "deliverables": "1 | Individual development plans for all partial-fit people | Week 3\n2 | Training budget and timeline | Week 4\n3 | Certification paths identified | Week 4\n4 | Coaching and mentoring pairings | Week 5\n5 | HR sign-off on development approach | Week 6",
    },
    "Define transition waves and sequencing logic": {
        "responsible_person": "CIO",
        "team_members": "CIO + HR + IT Leadership + Transformation PMO",
        "handover_organization": "HR + IT Leadership",
        "impact_rationale": "Unsequenced role changes create chaos. Wave planning ensures dependencies are respected, business continuity is maintained, and people experience the transition as structured rather than chaotic.",
        "deliverables": "1 | Wave definition document (Wave 1-4 with triggers) | Week 3\n2 | Dependency map between role changes | Week 4\n3 | Alignment with SAP and transformation milestones | Week 5\n4 | Rollback considerations per wave | Week 5\n5 | Go/no-go criteria per wave | Week 6",
    },
    "Plan stakeholder communication and change support": {
        "responsible_person": "CIO",
        "team_members": "CIO + HR Business Partner + Communications + IT Leadership",
        "handover_organization": "HR",
        "impact_rationale": "Trust is the CIO's most valuable asset during transition. A botched communication destroys months of relationship building. Every affected individual deserves a clear, honest, timely conversation before any public announcement.",
        "deliverables": "1 | Communication plan with timeline | Week 3\n2 | 1:1 conversation scripts per impact type | Week 4\n3 | FAQ document for affected individuals | Week 4\n4 | Town-hall preparation materials | Week 5\n5 | HR co-ownership agreement | Week 5\n6 | Manager briefing pack | Week 6",
    },
    "Determine sourcing path per role cluster": {
        "responsible_person": "CIO",
        "team_members": "CIO + CFO + HR + IT Leadership + Procurement",
        "handover_organization": "HR + CFO + Procurement",
        "impact_rationale": "Sourcing decisions determine cost, speed, and risk of the transition. Without explicit per-role sourcing paths, hiring happens ad-hoc, nearshoring opportunities are missed, and cost control is lost.",
        "deliverables": "1 | Sourcing decision register per role | Week 3\n2 | Rationale document per decision | Week 4\n3 | Cost comparison across sourcing paths | Week 5\n4 | JD drafts for external hire roles | Week 5\n5 | Board presentation on sourcing strategy | Week 6",
    },
    "Assess Lithuania nearshoring feasibility": {
        "responsible_person": "CIO",
        "team_members": "CIO + Kaunas site leadership + HR (local and group) + IT Leadership",
        "handover_organization": "Kaunas site leadership + HR",
        "impact_rationale": "The Kaunas site already exists with IT staff. Expanding its IT remit is a lower-risk, faster path to cost optimisation than outsourcing. But feasibility depends on talent availability, language, and management overhead.",
        "deliverables": "1 | Lithuania IT talent market assessment | Week 2\n2 | Role-by-role nearshoring viability matrix | Week 3\n3 | Cost-benefit analysis | Week 4\n4 | Language and timezone fit assessment | Week 4\n5 | Management model for remote IT team | Week 5\n6 | Site leadership endorsement | Week 6",
    },
    "Evaluate outsourcing readiness and minimum scale": {
        "responsible_person": "CIO",
        "team_members": "CIO + CFO + Procurement + IT Leadership + Current ops leads",
        "handover_organization": "CFO + Procurement",
        "impact_rationale": "The CIO hypothesis is that outsourcing mass is insufficient. This initiative validates or challenges that with data, preventing either premature outsourcing or missed cost-saving opportunities.",
        "deliverables": "1 | Service tower assessment matrix | Week 2\n2 | Volume and complexity analysis per tower | Week 3\n3 | Minimum viable scale thresholds | Week 4\n4 | Vendor market scan | Week 4\n5 | Cost-benefit comparison per tower | Week 5\n6 | Recommendation per tower | Week 6",
    },
}

with app.app_context():
    updated = 0
    for ini in Initiative.query.filter_by(organization_id=ORG_ID).all():
        data = FORMS.get(ini.name)
        if data:
            for field, value in data.items():
                setattr(ini, field, value)
            # Clear the wrong 'team' field if it was set
            if hasattr(ini, 'team') and ini.team:
                ini.team = None
            updated += 1
            f, t, s = ini.get_form_completion()
            print(f"  {f}/{t} ({s}): {ini.name[:50]}")

    db.session.commit()
    print(f"\nUpdated {updated} initiative forms")
