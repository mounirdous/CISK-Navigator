"""
Create People & Transition Readiness space in IT Function Target workspace.
Run: cd C:\code\CISK-Navigator && source venv/Scripts/activate && python scripts/create_people_gap_space.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import (
    Organization, Space, Challenge, Initiative, System, KPI, ValueType,
    GovernanceBody, KPIGovernanceBodyLink, KPIValueTypeConfig,
    ChallengeInitiativeLink, InitiativeSystemLink,
)

app = create_app()

ORG_ID = 24  # IT Function Target

# ── New Value Types ──────────────────────────────────────────────────────
NEW_VALUE_TYPES = [
    {
        "name": "Fit score",
        "kind": "level",
        "description": "How well the current person or capability matches the target role requirement. 1=significant gap, 2=partial fit (coachable), 3=strong fit.",
        "default_aggregation_formula": "avg",
    },
    {
        "name": "Readiness",
        "kind": "level",
        "description": "How soon this role or capability gap can be closed. 1=needs 6+ months or external hire, 2=achievable in 3-6 months with development, 3=ready now or within weeks.",
        "default_aggregation_formula": "min",
    },
    {
        "name": "Transition risk",
        "kind": "risk",
        "description": "Risk to the organisation if this role transition does not land well. 1=manageable, 2=significant disruption likely, 3=critical — could stall transformation.",
        "default_aggregation_formula": "max",
    },
]

# ── Structure: Challenges → Initiatives → Systems → KPIs ────────────────
STRUCTURE = {
    "space": {
        "name": "People & Transition Readiness",
        "description": "Gap analysis space used to assess how well current IT people and capabilities fit the target organisation design. Measures person-to-role fit, readiness to fill gaps, and transition risk — supporting the CIO's June deadline for a complete gap picture.",
        "space_label": "Gap Analysis",
        "display_order": 5,
        "swot": {
            "strengths": "• Deep institutional knowledge in existing team\n• Several multi-skilled individuals who bridge domains\n• Strong operational discipline in infrastructure and support\n• Leadership trust built during onboarding phase",
            "weaknesses": "• No formal role-to-person mapping exists today\n• Capability depth is uneven — some areas rely on single individuals\n• Limited project/change delivery bench strength\n• Skills gap in cloud, data, and modern architecture roles",
            "opportunities": "• Transformation program creates natural moment for role redesign\n• New hires can be shaped to target model from day one\n• Partner ecosystem can fill interim gaps while building internal capability\n• Cross-training and rotation can accelerate readiness",
            "threats": "• Key-person departures before successors are ready\n• Resistance to role changes if not handled transparently\n• Budget constraints limiting external hiring speed\n• Transformation timeline pressure conflicting with people development pace",
        },
    },
    "challenges": [
        {
            "name": "Role-to-person fit across the target organisation",
            "description": "For each major role cluster in the target IT function, assess how well current people map to target expectations — identifying strong fits, coachable gaps, and positions that require external sourcing.",
            "initiatives": [
                {
                    "name": "Assess business-facing and service ownership role fit",
                    "description": "Map current people to target business-facing IT roles: business relationship managers, service owners, demand managers. Identify who fits, who needs development, and where external hires are needed.",
                    "mission": "Deliver a clear person-to-role fit picture for all business-facing IT positions by June 2026.",
                    "success_criteria": "Every target business-facing role has a named candidate with a documented fit score, development plan, or sourcing decision.",
                    "systems": [
                        {
                            "name": "Business-facing role family",
                            "description": "Roles that interface directly with business divisions: IT Business Partners, Service Owners, Demand Managers, Business Analysts.",
                            "kpis": [
                                "% business-facing roles with named candidate",
                                "Average fit score for business-facing roles",
                                "Readiness of business-facing role pipeline",
                                "Transition risk in business-facing roles",
                                "Trust in role-assignment fairness",
                            ],
                        },
                    ],
                },
                {
                    "name": "Assess application, architecture and data role fit",
                    "description": "Map current people to target application leadership, architecture, and data roles: domain owners, solution architects, data stewards, integration leads.",
                    "mission": "Complete fit assessment for all application, architecture, and data roles by June 2026.",
                    "success_criteria": "Every target role in this cluster has a documented fit score with clear next steps (develop, move, hire).",
                    "systems": [
                        {
                            "name": "Application & architecture role family",
                            "description": "Roles covering application domain ownership, enterprise/solution architecture, data governance, BI/AI, and integration leadership.",
                            "kpis": [
                                "% application & architecture roles with named candidate",
                                "Average fit score for application & architecture roles",
                                "Readiness of application & architecture pipeline",
                                "Transition risk in application & architecture roles",
                                "Clarity of domain-ownership assignments",
                            ],
                        },
                    ],
                },
                {
                    "name": "Assess infrastructure, operations and security role fit",
                    "description": "Map current people to target infrastructure, operations, security, and site-support roles: infra leads, service desk managers, security officers, site IT coordinators.",
                    "mission": "Complete fit assessment for all infrastructure, operations, and security roles by June 2026.",
                    "success_criteria": "Every target role has a named candidate or sourcing plan with documented timeline.",
                    "systems": [
                        {
                            "name": "Infrastructure & security role family",
                            "description": "Roles covering infrastructure platform ownership, service operations, cybersecurity, IAM, site IT support, and digital workplace.",
                            "kpis": [
                                "% infrastructure & security roles with named candidate",
                                "Average fit score for infrastructure & security roles",
                                "Readiness of infrastructure & security pipeline",
                                "Transition risk in infrastructure & security roles",
                                "Resilience of critical infrastructure role coverage",
                            ],
                        },
                    ],
                },
                {
                    "name": "Assess governance, PMO and delivery role fit",
                    "description": "Map current people to target governance, portfolio management, project delivery, and change management roles.",
                    "mission": "Complete fit assessment for all governance and delivery roles by June 2026.",
                    "success_criteria": "PMO, portfolio, project management, and change roles all have fit assessments with development or sourcing decisions.",
                    "systems": [
                        {
                            "name": "Governance & delivery role family",
                            "description": "Roles covering IT governance forums, portfolio management, project/program delivery, change management, vendor management, and financial control.",
                            "kpis": [
                                "% governance & delivery roles with named candidate",
                                "Average fit score for governance & delivery roles",
                                "Readiness of governance & delivery pipeline",
                                "Transition risk in governance & delivery roles",
                                "Decision readiness on PMO model",
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "name": "Capability depth and development priorities",
            "description": "Beyond individual role fit, assess whether the overall IT function has sufficient depth, bench strength, and development momentum to sustain the target operating model — especially in areas where single-point-of-failure risk is high.",
            "initiatives": [
                {
                    "name": "Map critical capability gaps and single-person dependencies",
                    "description": "Identify areas where the target model requires capabilities that don't exist today or where knowledge is concentrated in one person. Prioritise development, cross-training, or external hiring.",
                    "mission": "Produce a prioritised capability gap register with mitigation actions by June 2026.",
                    "success_criteria": "Every critical capability area has a documented gap severity, mitigation plan, and owner.",
                    "systems": [
                        {
                            "name": "Capability gap register",
                            "description": "Structured register of capability gaps: what's missing, how critical, what's the plan (develop, hire, outsource, partner).",
                            "kpis": [
                                "% critical capabilities with documented gap analysis",
                                "Number of single-person dependencies identified",
                                "% gaps with mitigation plan defined",
                                "Risk of capability shortfall in next 12 months",
                                "Coverage of cross-training initiatives",
                            ],
                        },
                    ],
                },
                {
                    "name": "Define development and upskilling priorities",
                    "description": "For people who are a partial fit (fit score = 2), define specific development actions: training, coaching, rotation, mentoring, certification. Align with HR development budget and timeline.",
                    "mission": "Deliver a prioritised development plan for all coachable-gap individuals by June 2026.",
                    "success_criteria": "Every person with fit score 2 has a named development path with timeline, cost estimate, and HR alignment.",
                    "systems": [
                        {
                            "name": "Development & upskilling plan",
                            "description": "Individual and team development actions: formal training, coaching, job rotation, shadowing, certification paths, conference attendance.",
                            "kpis": [
                                "% coachable-gap individuals with development plan",
                                "Clarity of development priorities and sequencing",
                                "HR alignment on development budget and timeline",
                                "Trust in development opportunity fairness",
                                "Risk of development plan not delivering in time",
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "name": "Transition sequencing, risk and communication",
            "description": "Plan the sequence of role changes, organisational moves, and external hires — managing the human and operational risk of transition while maintaining business continuity and trust.",
            "initiatives": [
                {
                    "name": "Define transition waves and sequencing logic",
                    "description": "Not everything can move at once. Define which role changes happen first (quick wins, critical gaps) and which need more time (complex hand-offs, external searches). Align with transformation program milestones.",
                    "mission": "Produce a phased transition roadmap with clear wave definitions by June 2026.",
                    "success_criteria": "Transition waves are defined with triggers, dependencies, and rollback considerations.",
                    "systems": [
                        {
                            "name": "Transition roadmap",
                            "description": "Phased plan showing which roles move when, dependencies between moves, and alignment with broader transformation milestones.",
                            "kpis": [
                                "% target roles assigned to a transition wave",
                                "Clarity of transition sequencing logic",
                                "Risk of transition timing conflicts",
                                "Readiness of wave-1 moves",
                                "Alignment with transformation program milestones",
                            ],
                        },
                    ],
                },
                {
                    "name": "Plan stakeholder communication and change support",
                    "description": "Role changes affect real people. Plan how to communicate the target model, individual fit assessments, and development opportunities — with transparency and fairness as non-negotiable principles.",
                    "mission": "Deliver a communication and change plan that maintains trust through the transition.",
                    "success_criteria": "Every affected individual has a clear, honest conversation before any public announcement. HR is co-owner of the communication plan.",
                    "systems": [
                        {
                            "name": "Communication & change plan",
                            "description": "Stakeholder communication sequences, 1:1 conversation scripts, FAQ documents, town-hall preparation, feedback channels.",
                            "kpis": [
                                "% affected individuals with 1:1 conversation completed",
                                "Trust in transition communication fairness",
                                "Clarity of communication plan and timeline",
                                "HR co-ownership of communication approach",
                                "Risk of trust erosion during transition",
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}

# ── GB assignments per KPI (which GBs care about this KPI) ──────────────
# Map KPI name patterns to GB abbreviations
DEFAULT_GBS = ["ITLT", "HR", "EC"]  # IT Leadership, HR, Executive Committee
EXTRA_GBS = {
    "business-facing": ["DIV", "COO"],
    "application": ["CAB"],
    "infrastructure": ["SITES"],
    "governance": ["CFO"],
    "transition": ["COO", "DIV"],
    "communication": ["HR", "COO", "DIV"],
    "trust": ["HR"],
    "PMO": ["CFO"],
}


def get_gb_ids(kpi_name, gb_lookup):
    """Determine which GBs a KPI should be linked to based on name patterns."""
    ids = set()
    for abbr in DEFAULT_GBS:
        if abbr in gb_lookup:
            ids.add(gb_lookup[abbr])

    name_lower = kpi_name.lower()
    for pattern, abbrs in EXTRA_GBS.items():
        if pattern in name_lower:
            for abbr in abbrs:
                if abbr in gb_lookup:
                    ids.add(gb_lookup[abbr])
    return list(ids)


def main():
    with app.app_context():
        org = Organization.query.get(ORG_ID)
        if not org:
            print(f"Organization {ORG_ID} not found!")
            return

        print(f"Working on: {org.name} (ID={org.id})")

        # Build GB lookup
        gbs = GovernanceBody.for_org(ORG_ID)
        gb_lookup = {gb.abbreviation: gb.id for gb in gbs}
        gb_lookup.update({gb.name: gb.id for gb in gbs})
        print(f"GBs available: {list(gb_lookup.keys())}")

        # Get existing value types
        existing_vts = {vt.name: vt for vt in ValueType.query.filter_by(organization_id=ORG_ID).all()}
        max_vt_order = max((vt.display_order for vt in existing_vts.values()), default=0)

        # Create new value types
        vt_map = {}
        for vt_data in NEW_VALUE_TYPES:
            if vt_data["name"] in existing_vts:
                vt_map[vt_data["name"]] = existing_vts[vt_data["name"]]
                print(f"  VT exists: {vt_data['name']}")
            else:
                max_vt_order += 1
                vt = ValueType(
                    organization_id=ORG_ID,
                    name=vt_data["name"],
                    kind=vt_data["kind"],
                    description=vt_data["description"],
                    default_aggregation_formula=vt_data["default_aggregation_formula"],
                    display_order=max_vt_order,
                    is_active=True,
                )
                db.session.add(vt)
                db.session.flush()
                vt_map[vt_data["name"]] = vt
                print(f"  VT created: {vt_data['name']} (ID={vt.id})")

        # Also map existing VTs for KPI config
        for vt in existing_vts.values():
            vt_map[vt.name] = vt

        # KPI → value type mapping
        KPI_VT_MAP = {
            "% ": ["Coverage", "Fit score"],
            "Average fit": ["Fit score"],
            "Readiness": ["Readiness"],
            "Transition risk": ["Transition risk"],
            "Risk": ["Risk", "Transition risk"],
            "Trust": ["Trust"],
            "Clarity": ["Clarity"],
            "Decision": ["Decision effectiveness"],
            "Coverage": ["Coverage"],
            "Resilience": ["Resilience"],
            "Number of": ["Coverage"],
            "HR ": ["Trust", "Clarity"],
            "Alignment": ["Clarity", "Fit score"],
        }

        def get_vt_ids(kpi_name):
            """Get value type IDs for a KPI based on name patterns."""
            matched = set()
            name_lower = kpi_name.lower()
            for pattern, vt_names in KPI_VT_MAP.items():
                if pattern.lower() in name_lower:
                    for vt_name in vt_names:
                        if vt_name in vt_map:
                            matched.add(vt_map[vt_name].id)
            # Always add Fit score for % KPIs, Transition risk for risk KPIs
            if not matched:
                if "fit" in name_lower:
                    matched.add(vt_map["Fit score"].id)
                elif "risk" in name_lower:
                    matched.add(vt_map["Transition risk"].id)
                elif "readiness" in name_lower or "ready" in name_lower:
                    matched.add(vt_map["Readiness"].id)
                else:
                    matched.add(vt_map["Clarity"].id)
            return list(matched)

        # Create the Space
        sd = STRUCTURE["space"]
        space = Space(
            organization_id=ORG_ID,
            name=sd["name"],
            description=sd["description"],
            space_label=sd.get("space_label"),
            display_order=sd.get("display_order", 5),
            is_private=False,
        )
        # SWOT
        swot = sd.get("swot", {})
        space.swot_strengths = swot.get("strengths")
        space.swot_weaknesses = swot.get("weaknesses")
        space.swot_opportunities = swot.get("opportunities")
        space.swot_threats = swot.get("threats")

        db.session.add(space)
        db.session.flush()
        print(f"\nSpace created: {space.name} (ID={space.id})")

        # Create Challenges, Initiatives, Systems, KPIs
        for ch_data in STRUCTURE["challenges"]:
            challenge = Challenge(
                organization_id=ORG_ID,
                space_id=space.id,
                name=ch_data["name"],
                description=ch_data["description"],
            )
            db.session.add(challenge)
            db.session.flush()
            print(f"  Challenge: {challenge.name} (ID={challenge.id})")

            for init_data in ch_data["initiatives"]:
                initiative = Initiative(
                    organization_id=ORG_ID,
                    name=init_data["name"],
                    description=init_data["description"],
                    mission=init_data.get("mission"),
                    success_criteria=init_data.get("success_criteria"),
                )
                db.session.add(initiative)
                db.session.flush()

                # Link to challenge
                cl = ChallengeInitiativeLink(
                    challenge_id=challenge.id,
                    initiative_id=initiative.id,
                )
                db.session.add(cl)
                db.session.flush()
                print(f"    Initiative: {initiative.name} (ID={initiative.id})")

                for sys_data in init_data["systems"]:
                    system = System(
                        organization_id=ORG_ID,
                        name=sys_data["name"],
                        description=sys_data["description"],
                    )
                    db.session.add(system)
                    db.session.flush()

                    # Link system to initiative
                    isl = InitiativeSystemLink(
                        initiative_id=initiative.id,
                        system_id=system.id,
                    )
                    db.session.add(isl)
                    db.session.flush()
                    print(f"      System: {system.name} (ID={system.id}, link={isl.id})")

                    for kpi_name in sys_data["kpis"]:
                        kpi = KPI(
                            initiative_system_link_id=isl.id,
                            name=kpi_name,
                        )
                        db.session.add(kpi)
                        db.session.flush()

                        # Add value type configs
                        for vt_id in get_vt_ids(kpi_name):
                            config = KPIValueTypeConfig(
                                kpi_id=kpi.id,
                                value_type_id=vt_id,
                            )
                            db.session.add(config)

                        # Add GB links
                        for gb_id in get_gb_ids(kpi_name, gb_lookup):
                            gb_link = KPIGovernanceBodyLink(
                                kpi_id=kpi.id,
                                governance_body_id=gb_id,
                            )
                            db.session.add(gb_link)

                        print(f"        KPI: {kpi_name}")

        # Create milestone: Gap Analysis deadline mid-June
        from app.models import ActionItem
        from datetime import date
        milestone = ActionItem(
            organization_id=ORG_ID,
            type="milestone",
            title="Gap Analysis Complete — CIO Deadline",
            description="**Deliverable:** Complete people-to-role gap analysis across all target IT function role families.\n\n**What 'done' looks like:**\n- Every target role has a named candidate with fit score\n- All capability gaps documented with mitigation plans\n- Transition waves defined with sequencing logic\n- Communication plan co-owned with HR\n- Board-ready summary for CIO presentation",
            status="active",
            priority="urgent",
            is_global=False,
            due_date=date(2026, 6, 15),
            visibility="shared",
            owner_user_id=1,  # Will be updated — using first user
            created_by_user_id=1,
        )
        # Set tags if available
        milestone.tags = ["deadline", "review"]
        db.session.add(milestone)

        # Also create key action items for the gap analysis
        actions_data = [
            ("Map all target roles to current people", date(2026, 5, 15), "action", "Map every role in the target IT function design to a current person (or mark as vacant). Use the CISK workspace to document fit scores."),
            ("Complete capability gap register", date(2026, 5, 31), "action", "Document all critical capability gaps, single-person dependencies, and mitigation plans (develop, hire, outsource, partner)."),
            ("Define transition waves", date(2026, 6, 7), "action", "Group role changes into phased waves. Define wave-1 (quick wins), wave-2 (requires development), wave-3 (external hire). Align with transformation milestones."),
            ("Prepare CIO gap analysis presentation", date(2026, 6, 12), "action", "Board-ready summary showing: target vs current, fit scores by role family, top gaps, transition roadmap, cost/risk implications."),
            ("Complete HR alignment conversations", date(2026, 6, 10), "action", "Ensure HR is co-owner of development plans, communication approach, and any restructuring implications."),
        ]
        from app.models import User
        owner = User.query.filter_by(login="moun").first() or User.query.first()
        for title, due, atype, desc in actions_data:
            ai = ActionItem(
                organization_id=ORG_ID,
                type=atype,
                title=title,
                description=desc,
                status="active",
                priority="high",
                due_date=due,
                visibility="shared",
                owner_user_id=owner.id,
                created_by_user_id=owner.id,
            )
            db.session.add(ai)
            print(f"  Action: {title} (due {due})")

        milestone.owner_user_id = owner.id
        milestone.created_by_user_id = owner.id

        db.session.commit()
        print(f"\n✅ Done! Space '{sd['name']}' created with all entities.")
        print(f"✅ Milestone 'Gap Analysis Complete' set for June 15, 2026")
        print(f"✅ 5 action items created with deadlines leading to milestone")
        print("Export the workspace to get the updated backup.")


if __name__ == "__main__":
    main()
