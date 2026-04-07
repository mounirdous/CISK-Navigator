"""Create sourcing strategy challenge in People & Transition Readiness space."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from app import create_app
from app.extensions import db
from app.models import (
    Organization, Space, Challenge, Initiative, System, KPI, ValueType,
    GovernanceBody, KPIGovernanceBodyLink, KPIValueTypeConfig,
    ChallengeInitiativeLink, InitiativeSystemLink, Contribution, User,
    ActionItem, ActionItemMention,
)
from datetime import date
app = create_app()
ORG_ID = 24

with app.app_context():
    user = User.query.filter_by(login="moun").first()
    space = Space.query.filter_by(organization_id=ORG_ID, name="People & Transition Readiness").first()

    # Clean up VTs that should not exist
    for name in ("Sourcing path", "Publication readiness"):
        vt = ValueType.query.filter_by(organization_id=ORG_ID, name=name).first()
        if vt:
            for cfg in KPIValueTypeConfig.query.filter_by(value_type_id=vt.id).all():
                Contribution.query.filter_by(kpi_value_type_config_id=cfg.id).delete()
                db.session.delete(cfg)
            db.session.delete(vt)
            print(f"Deleted VT: {name}")

    gbs = GovernanceBody.for_org(ORG_ID)
    gb_lookup = {}
    for gb in gbs:
        gb_lookup[gb.abbreviation] = gb.id
        gb_lookup[gb.name] = gb.id

    vt_map = {vt.name: vt for vt in ValueType.query.filter_by(organization_id=ORG_ID, is_active=True).all()}
    coverage = vt_map["Coverage"]
    clarity = vt_map["Clarity"]
    trust = vt_map["Trust"]
    risk = vt_map["Risk"]
    t_risk = vt_map["Transition risk"]
    readiness = vt_map["Readiness"]

    all_gbs = [g for g in [
        gb_lookup.get("ITLT"), gb_lookup.get("HR"), gb_lookup.get("EC"),
        gb_lookup.get("CFO"), gb_lookup.get("COO"), gb_lookup.get("PROC"), gb_lookup.get("SITES"),
    ] if g]

    ch = Challenge(
        organization_id=ORG_ID, space_id=space.id,
        name="Sourcing path, location, and cost decisions",
        description="Determine sourcing strategy per gap: develop, hire, nearshore Lithuania, outsource, or partner.",
    )
    db.session.add(ch)
    db.session.flush()
    print(f"Challenge: {ch.name}")

    def make(name, desc, mission, success, sys_name, sys_desc, kpi_defs):
        ini = Initiative(organization_id=ORG_ID, name=name, description=desc, mission=mission, success_criteria=success)
        db.session.add(ini); db.session.flush()
        db.session.add(ChallengeInitiativeLink(challenge_id=ch.id, initiative_id=ini.id)); db.session.flush()
        s = System(organization_id=ORG_ID, name=sys_name, description=sys_desc)
        db.session.add(s); db.session.flush()
        isl = InitiativeSystemLink(initiative_id=ini.id, system_id=s.id)
        db.session.add(isl); db.session.flush()
        for kpi_name, vts in kpi_defs:
            kpi = KPI(initiative_system_link_id=isl.id, name=kpi_name)
            db.session.add(kpi); db.session.flush()
            for vt in vts:
                db.session.add(KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=vt.id))
            for gb_id in all_gbs:
                db.session.add(KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=gb_id))
            db.session.flush()
            for vt in vts:
                cfg = KPIValueTypeConfig.query.filter_by(kpi_id=kpi.id, value_type_id=vt.id).first()
                c = Contribution(kpi_value_type_config_id=cfg.id,
                                 contributor_name=user.display_name or user.login, comment="Initial baseline")
                c.numeric_value = 0 if vt.kind == "numeric" else None
                c.qualitative_level = 1 if vt.kind != "numeric" else None
                db.session.add(c)
            print(f"  KPI: {kpi_name}")
        return ini

    i1 = make(
        "Determine sourcing path per role cluster",
        "For each role family, decide: develop, hire, nearshore Lithuania, outsource, or partner.",
        "Every target role has a sourcing decision by June 2026.",
        "100% roles with sourcing path. External roles have draft JDs. Cost comparison done.",
        "Role sourcing decision register",
        "Structured register: path, rationale, cost, timeline, dependencies per role.",
        [
            ("% target roles with sourcing path decided", [coverage, clarity]),
            ("Clarity of sourcing rationale per role cluster", [clarity, trust]),
            ("Risk of sourcing path not delivering in time", [t_risk]),
            ("Trust in sourcing decision fairness", [trust]),
            ("Readiness of external hiring pipeline", [readiness, coverage]),
        ],
    )

    i2 = make(
        "Assess Lithuania nearshoring feasibility",
        "Which roles can staff from Kaunas? Talent, language, timezone, cost, overhead.",
        "Feasibility assessment with role recommendations by June 2026.",
        "Nearshore-viable roles listed. Cost-benefit done. Site leadership consulted.",
        "Lithuania nearshoring assessment",
        "Feasibility: talent pool, cost model, language, timezone, management overhead.",
        [
            ("% roles assessed for nearshoring viability", [coverage]),
            ("Clarity of Lithuania talent availability", [clarity]),
            ("Cost differential estimate nearshore vs local", [clarity, risk]),
            ("Risk of management overhead exceeding savings", [t_risk]),
            ("Readiness of Kaunas site for IT staffing", [readiness]),
            ("Trust in nearshoring approach from local teams", [trust]),
        ],
    )

    i3 = make(
        "Evaluate outsourcing readiness and minimum scale",
        "Does IT have enough mass for outsourcing? Which towers? Minimum scope?",
        "Data-driven outsourcing feasibility by June 2026.",
        "Towers assessed. Min scale documented. Cost-benefit per tower. Clear recommendation.",
        "Outsourcing readiness assessment",
        "Viability per tower: volume, complexity, vendor market, cost-benefit, min scope.",
        [
            ("% service towers assessed for outsourcing", [coverage]),
            ("Clarity of minimum-scale requirements", [clarity]),
            ("Risk of outsourcing before sufficient mass", [t_risk, risk]),
            ("Readiness of service documentation for handover", [readiness]),
            ("Vendor market assessment coverage", [coverage, clarity]),
        ],
    )

    for title, due, init, desc in [
        ("Assess Lithuania talent pool for IT roles", date(2026, 5, 20), i2,
         "Research Kaunas/Vilnius IT talent. Salary benchmarks, language, universities."),
        ("Draft external JDs for critical gap roles", date(2026, 5, 25), i1,
         "For fit=1 roles where development not viable, draft JDs. HR budget alignment."),
        ("Evaluate outsourcing scale for infra ops", date(2026, 5, 30), i3,
         "Assess infra ops volume. Get vendor indicative quotes."),
        ("Present sourcing strategy to CIO and CFO", date(2026, 6, 10), i1,
         "Deck: sourcing path per role family with cost comparison and risk view."),
    ]:
        ai = ActionItem(organization_id=ORG_ID, type="action", title=title,
                        description=desc, status="active", priority="high",
                        due_date=due, visibility="shared",
                        owner_user_id=user.id, created_by_user_id=user.id)
        db.session.add(ai); db.session.flush()
        db.session.add(ActionItemMention(action_item_id=ai.id, entity_type="initiative",
                                         entity_id=init.id, mention_text=init.name))
        print(f"  Action: {title}")

    db.session.commit()
    print("\nDone! 1 challenge, 3 initiatives, 3 systems, 16 KPIs, 4 actions")
