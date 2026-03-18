"""
Demo Data Generation Service

Creates complete, realistic demo organizations with full feature coverage:
- Fun, non-technical scenarios (Sport Club, Personal Health, Sustainability)
- Complete entity hierarchy (spaces, challenges, initiatives, systems, KPIs)
- Stakeholders with realistic profiles and influence/interest levels
- Stakeholder maps with relationship networks
- Entity-stakeholder links (owners, reviewers, contributors)
- Historical snapshots across multiple time periods
- KPIs with different frequencies (daily, weekly, monthly, quarterly, yearly)
- Linked KPIs and formula KPIs
- Mix of public/private spaces
- Action items in various states
"""

import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import (
    KPI,
    ActionItem,
    Challenge,
    ChallengeInitiativeLink,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPISnapshot,
    KPIValueTypeConfig,
    Organization,
    Space,
    Stakeholder,
    StakeholderMap,
    StakeholderMapMembership,
    StakeholderRelationship,
    System,
    User,
    ValueType,
)


class DemoDataService:
    """Service for generating comprehensive demo data"""

    # Demo scenarios with complete entity hierarchies
    SCENARIOS = {
        "riverside_fc": {
            "name": "Riverside FC",
            "description": "Community football club focused on youth development and community engagement",
            "porters": {
                "new_entrants": "Low threat - Established brand and loyal fanbase make it difficult for new clubs to attract players and supporters in our catchment area.",
                "suppliers": "Medium power - Limited pool of qualified youth coaches and dependence on local sports equipment suppliers gives them moderate bargaining power.",
                "buyers": "High power - Parents and guardians choose where children train, making retention critical. Season ticket holders have many entertainment alternatives.",
                "substitutes": "High threat - Video games, other sports (rugby, cricket), and non-sport activities compete heavily for youth attention and family time.",
                "rivalry": "Medium intensity - Three other local clubs compete for talent, but collaboration on referee costs and facility sharing reduces direct confrontation.",
            },
            "spaces": [
                {
                    "name": "Youth Academy",
                    "description": "Developing the next generation of players",
                    "is_private": False,
                    "swot": {
                        "strengths": "Excellent coaching staff with UEFA licenses. Modern training facilities with full-size pitch. Strong reputation for player development - 3 players moved to professional clubs in last 2 years.",
                        "weaknesses": "Limited budget for international tournaments. Aging gym equipment needs replacement. Parent volunteer burnout affecting administrative support.",
                        "opportunities": "New partnership with local university for sports science support. Growing interest in girls' football presenting expansion potential. Council considering grant for facility upgrades.",
                        "threats": "Premier League academy 15 miles away poaching top talent. Rising insurance costs threatening program sustainability. Declining birth rates in catchment area reducing player pool.",
                    },
                    "challenges": [
                        {
                            "name": "Player Development",
                            "description": "Train and develop young talent",
                            "initiatives": [
                                {
                                    "name": "U16 Training Program",
                                    "description": "Structured training for under-16s",
                                    "systems": [
                                        {
                                            "name": "Training Sessions",
                                            "kpis": [
                                                {"name": "Weekly Training Hours", "frequency": "weekly"},
                                                {"name": "Daily Attendance Rate", "frequency": "daily"},
                                                {"name": "Monthly Skills Assessment", "frequency": "monthly"},
                                            ],
                                        },
                                        {
                                            "name": "Player Fitness",
                                            "kpis": [
                                                {"name": "Quarterly Fitness Test Scores", "frequency": "quarterly"},
                                                {"name": "Weekly Recovery Time", "frequency": "weekly"},
                                            ],
                                        },
                                    ],
                                },
                                {
                                    "name": "Talent Scouting",
                                    "description": "Identify and recruit promising players",
                                    "systems": [
                                        {
                                            "name": "Scouting Network",
                                            "kpis": [
                                                {"name": "Monthly New Prospects", "frequency": "monthly"},
                                                {"name": "Yearly Recruitment Success Rate", "frequency": "yearly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "name": "Community Engagement",
                            "description": "Build strong ties with local community",
                            "initiatives": [
                                {
                                    "name": "Local Schools Partnership",
                                    "description": "Partner with schools for after-school programs",
                                    "systems": [
                                        {
                                            "name": "School Programs",
                                            "kpis": [
                                                {"name": "Weekly Participating Students", "frequency": "weekly"},
                                                {"name": "Quarterly Program Satisfaction", "frequency": "quarterly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "name": "First Team",
                    "description": "Senior competitive team",
                    "is_private": False,
                    "swot": {
                        "strengths": "Experienced manager with proven promotion record. Balanced squad with mix of youth and experience. Strong home record (75% win rate at Riverside Stadium). Passionate fan base averaging 800 attendance.",
                        "weaknesses": "Thin squad depth - injuries expose lack of cover. Aging defensive line needs refresh. Poor away form (only 30% win rate). Limited transfer budget compared to league rivals.",
                        "opportunities": "Three key rivals lost managers in off-season creating instability. New sponsorship deal could fund two quality signings. Local media interest growing with promotion push. Potential cup run generating additional revenue.",
                        "threats": "Wealthy new owners at rival club enabling aggressive recruitment. Player wage demands increasing beyond sustainable levels. Pitch drainage issues causing fixture postponements. Key striker attracting interest from higher divisions.",
                    },
                    "challenges": [
                        {
                            "name": "League Performance",
                            "description": "Achieve promotion to higher division",
                            "initiatives": [
                                {
                                    "name": "Season Campaign",
                                    "description": "Win matches and climb the table",
                                    "systems": [
                                        {
                                            "name": "Match Performance",
                                            "kpis": [
                                                {"name": "Weekly Match Results", "frequency": "weekly"},
                                                {"name": "Monthly League Position", "frequency": "monthly"},
                                                {"name": "Yearly Goals Scored", "frequency": "yearly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Club Operations",
                    "description": "Financial and operational management",
                    "is_private": True,
                    "swot": {
                        "strengths": "Debt-free operation with cash reserves. Diversified revenue (membership 40%, tickets 35%, sponsorship 15%, grants 10%). Professional finance team with sports industry experience. Strong governance structure with independent board oversight.",
                        "weaknesses": "Heavy reliance on volunteer labor creating succession planning risk. Outdated IT systems causing reporting delays. No dedicated fundraising role. Limited commercial exploitation of brand and facilities.",
                        "opportunities": "Naming rights for stadium could generate £50k annually. Facility hire for birthday parties and corporate events underutilized. E-commerce potential for branded merchandise. Cryptocurrency payment acceptance appealing to younger demographic.",
                        "threats": "Energy price increases affecting facility operating costs. Living wage legislation impacting part-time staff costs. Cyber security risks with online payment systems. Regulatory changes requiring expensive facility modifications (accessibility compliance).",
                    },
                    "challenges": [
                        {
                            "name": "Financial Sustainability",
                            "description": "Maintain healthy finances",
                            "initiatives": [
                                {
                                    "name": "Revenue Growth",
                                    "description": "Increase revenue streams",
                                    "systems": [
                                        {
                                            "name": "Membership & Tickets",
                                            "kpis": [
                                                {"name": "Monthly Membership Revenue", "frequency": "monthly"},
                                                {"name": "Weekly Ticket Sales", "frequency": "weekly"},
                                                {"name": "Yearly Total Revenue", "frequency": "yearly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            ],
            "stakeholders": [
                {"name": "Sarah Mitchell", "role": "Head Coach", "influence": 5, "interest": 5},
                {"name": "James O'Connor", "role": "Youth Academy Director", "influence": 4, "interest": 5},
                {"name": "Emma Thompson", "role": "Club President", "influence": 5, "interest": 4},
                {"name": "David Chen", "role": "Finance Director", "influence": 4, "interest": 3},
                {"name": "Lisa Rodriguez", "role": "Community Liaison", "influence": 3, "interest": 5},
                {"name": "Tom Harrison", "role": "Team Captain", "influence": 3, "interest": 5},
                {"name": "Rachel Green", "role": "Marketing Manager", "influence": 2, "interest": 4},
                {"name": "Michael Brown", "role": "Local Council Representative", "influence": 4, "interest": 3},
            ],
            "stakeholder_maps": [
                {
                    "name": "Youth Development Ecosystem",
                    "description": "Key stakeholders in youth player development",
                    "stakeholders": ["Sarah Mitchell", "James O'Connor", "Emma Thompson", "Lisa Rodriguez"],
                },
                {
                    "name": "Financial Governance",
                    "description": "Financial decision-making network",
                    "stakeholders": ["Emma Thompson", "David Chen", "Rachel Green"],
                },
            ],
        },
        "myhealth_journey": {
            "name": "MyHealth Journey",
            "description": "Personal health and wellness transformation",
            "porters": {
                "new_entrants": "High threat - Fitness apps, wearables, and online coaching platforms entering market daily with low barriers to entry and aggressive pricing.",
                "suppliers": "Low power - Abundant choice of gyms, fitness equipment, nutritionists, and therapists. Easy to switch providers with minimal switching costs.",
                "buyers": "High power - I control all decisions and budget allocation. Can easily pivot to different approaches, pause subscriptions, or switch providers based on results.",
                "substitutes": "Very high threat - Free alternatives abundant: YouTube fitness videos, free running, home bodyweight training, meditation apps (free tiers). Public parks and outdoor spaces.",
                "rivalry": "Medium intensity - While many health approaches exist, each serves different needs. Competition for time and attention rather than direct service rivalry.",
            },
            "spaces": [
                {
                    "name": "Physical Fitness",
                    "description": "Exercise and physical activity goals",
                    "is_private": False,
                    "swot": {
                        "strengths": "High motivation and clear goals (target weight 170 lbs). Gym membership paid through year-end eliminating financial excuse. Supportive partner willing to join activities. Previous athletic background making muscle memory advantage.",
                        "weaknesses": "Sedentary job (desk-bound 8+ hours daily). History of starting strong then fading after 6 weeks. Knee injury from 2023 limiting high-impact activities. Poor sleep schedule affecting recovery and energy.",
                        "opportunities": "Gym quiet at 6 AM reducing intimidation factor. Work-from-home Fridays enabling lunchtime workouts. Running club starting in neighborhood providing social motivation. Fitness tracker data revealing patterns for optimization.",
                        "threats": "Winter months historically trigger motivation decline. Work stress leading to missed sessions. Social events centered around unhealthy food. Injury risk from overtraining in early enthusiasm.",
                    },
                    "challenges": [
                        {
                            "name": "Weight Management",
                            "description": "Reach target weight through diet and exercise",
                            "initiatives": [
                                {
                                    "name": "Exercise Routine",
                                    "description": "Regular workout schedule",
                                    "systems": [
                                        {
                                            "name": "Cardio Training",
                                            "kpis": [
                                                {"name": "Daily Steps Count", "frequency": "daily"},
                                                {"name": "Weekly Running Distance", "frequency": "weekly"},
                                                {"name": "Monthly Cardio Hours", "frequency": "monthly"},
                                            ],
                                        },
                                        {
                                            "name": "Strength Training",
                                            "kpis": [
                                                {"name": "Weekly Gym Sessions", "frequency": "weekly"},
                                                {"name": "Quarterly Strength Gains", "frequency": "quarterly"},
                                            ],
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Nutrition",
                    "description": "Healthy eating and meal planning",
                    "is_private": False,
                    "swot": {
                        "strengths": "Enjoy cooking and trying new recipes. Food logging app habit established (42-day streak). Partner supportive and willing to eat healthier. Farmers market access every Saturday for fresh produce.",
                        "weaknesses": "Weekday lunch often skipped or replaced with vending machine snacks. Evening snacking habit while watching TV. Poor portion control at restaurants. Limited nutrition knowledge beyond basics.",
                        "opportunities": "Meal prep Sunday routine developing successfully. Nutritionist session booked for personalized plan. Healthy meal delivery trial offer received. Work cafeteria introducing healthier options next month.",
                        "threats": "Business travel disrupting meal routines (3-4 trips per quarter). Family dinners at in-laws featuring heavy, traditional food. Holiday season approaching with parties and events. Stress-eating pattern when work pressure increases.",
                    },
                    "challenges": [
                        {
                            "name": "Balanced Diet",
                            "description": "Maintain nutritious eating habits",
                            "initiatives": [
                                {
                                    "name": "Meal Planning",
                                    "description": "Plan and prepare healthy meals",
                                    "systems": [
                                        {
                                            "name": "Calorie Tracking",
                                            "kpis": [
                                                {"name": "Daily Calorie Intake", "frequency": "daily"},
                                                {"name": "Weekly Meal Prep Sessions", "frequency": "weekly"},
                                                {"name": "Monthly Weight Change", "frequency": "monthly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Mental Wellbeing",
                    "description": "Stress management and mental health",
                    "is_private": True,
                    "swot": {
                        "strengths": "Therapy sessions providing professional support and coping strategies. Meditation app streak building consistency (28 days). Journaling practice helping process emotions. Support network of close friends available.",
                        "weaknesses": "Tendency to internalize stress rather than discuss. Difficulty saying no to commitments. Phone/screen time affecting sleep quality. Perfectionist mindset creating unnecessary pressure.",
                        "opportunities": "Company offering mindfulness workshop series. Yoga studio opening near home with beginner classes. Vacation time accrued enabling proper mental health break. Therapy uncovering root causes enabling targeted work.",
                        "threats": "Work deadline season approaching (Q4 typically high stress). Family health situation creating worry and emotional drain. Financial stress from home repairs. Seasonal affective disorder history with winter months.",
                    },
                    "challenges": [
                        {
                            "name": "Stress Reduction",
                            "description": "Manage daily stress and anxiety",
                            "initiatives": [
                                {
                                    "name": "Mindfulness Practice",
                                    "description": "Daily meditation and relaxation",
                                    "systems": [
                                        {
                                            "name": "Meditation",
                                            "kpis": [
                                                {"name": "Daily Meditation Minutes", "frequency": "daily"},
                                                {"name": "Weekly Stress Level", "frequency": "weekly"},
                                                {"name": "Quarterly Mental Health Score", "frequency": "quarterly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            ],
            "stakeholders": [
                {"name": "Dr. Emily Watson", "role": "Primary Care Physician", "influence": 5, "interest": 4},
                {"name": "Mark Stevens", "role": "Personal Trainer", "influence": 4, "interest": 5},
                {"name": "Jennifer Lee", "role": "Nutritionist", "influence": 4, "interest": 5},
                {"name": "Chris Taylor", "role": "Yoga Instructor", "influence": 3, "interest": 4},
                {"name": "Amanda White", "role": "Therapist", "influence": 4, "interest": 3},
                {"name": "Robert Johnson", "role": "Accountability Partner", "influence": 2, "interest": 5},
            ],
            "stakeholder_maps": [
                {
                    "name": "Health Support Team",
                    "description": "Primary health and wellness advisors",
                    "stakeholders": ["Dr. Emily Watson", "Mark Stevens", "Jennifer Lee"],
                },
                {
                    "name": "Mental Health Support",
                    "description": "Mental wellbeing network",
                    "stakeholders": ["Amanda White", "Chris Taylor", "Robert Johnson"],
                },
            ],
        },
        "green_home": {
            "name": "Green Home Project",
            "description": "Transforming home into an eco-friendly sustainable living space",
            "porters": {
                "new_entrants": "Medium threat - Green technology becoming mainstream with new suppliers entering market, but technical expertise and certification requirements create some barriers.",
                "suppliers": "Medium power - Solar installers consolidating (fewer local options). But battery technology competition increasing choices. Water system suppliers abundant with low differentiation.",
                "buyers": "Medium power - We control timing and scope of upgrades, but major investments (solar, insulation) are significant enough that switching mid-project is costly.",
                "substitutes": "Low threat - While gradual approach possible (LED bulbs, smart thermostats), comprehensive sustainability requires dedicated systems. Renting instead of owning is only major substitute.",
                "rivalry": "Low intensity - Not competing with neighbors, though social proof matters for community adoption. Cooperation on bulk purchasing and contractor sharing reduces any competitive element.",
            },
            "spaces": [
                {
                    "name": "Energy Efficiency",
                    "description": "Reduce energy consumption and carbon footprint",
                    "is_private": False,
                    "swot": {
                        "strengths": "South-facing roof ideal for solar panels (unobstructed sun exposure). Recent home energy audit identified priority improvements. Government rebates covering 30% of solar installation cost. Strong electrical infrastructure supporting upgrades.",
                        "weaknesses": "Old HVAC system inefficient (15 years old). Single-pane windows in bedrooms causing heat loss. Insufficient attic insulation (R-19 vs recommended R-49). Initial capital required for upgrades straining budget.",
                        "opportunities": "Federal tax credits for energy improvements available through 2026. Utility offering net metering for solar (sell excess to grid). Energy prices projected to rise 15% over 3 years improving ROI. Neighbor successful installation providing lessons learned.",
                        "threats": "Solar technology improving rapidly (risk of early obsolescence). Interest rates making financing more expensive. Permitting delays in city (6-8 week backlog). HOA review process adding uncertainty to timeline.",
                    },
                    "challenges": [
                        {
                            "name": "Solar Energy Transition",
                            "description": "Install and optimize solar panels",
                            "initiatives": [
                                {
                                    "name": "Solar Panel Installation",
                                    "description": "Complete solar system setup",
                                    "systems": [
                                        {
                                            "name": "Energy Generation",
                                            "kpis": [
                                                {"name": "Daily Solar Output", "frequency": "daily"},
                                                {"name": "Weekly Energy Savings", "frequency": "weekly"},
                                                {"name": "Monthly Electricity Bill", "frequency": "monthly"},
                                                {"name": "Yearly Carbon Offset", "frequency": "yearly"},
                                            ],
                                        },
                                        {
                                            "name": "Solar Economics",
                                            "kpis": [
                                                {"name": "Monthly Installation Cost", "frequency": "monthly"},
                                                {"name": "Monthly Energy Revenue", "frequency": "monthly"},
                                                {"name": "Monthly Net Profit", "frequency": "monthly", "formula": True},
                                            ],
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Waste Reduction",
                    "description": "Minimize household waste",
                    "is_private": False,
                    "swot": {
                        "strengths": "Backyard space available for composting system. Family already recycling consistently (blue bin program). Reusable shopping bags habit established. Municipal composting pickup available weekly.",
                        "weaknesses": "Food waste significant (family of 4 throwing away ~30% of produce). Amazon packaging accumulation (3-4 boxes weekly). Single-use plastics still prevalent (water bottles, food storage). Kids resistant to reusable lunch containers.",
                        "opportunities": "Community sharing library reducing need to buy/own items. Bulk food store opened nearby (bring own containers). Upcycling workshop series at community center. Neighbor starting tool-sharing cooperative.",
                        "threats": "Convenience of disposables during busy weeks. Kids' activities generating single-use waste (sports drinks, snack packaging). Gift-giving occasions bringing unwanted items into home. Online shopping habit increasing packaging waste.",
                    },
                    "challenges": [
                        {
                            "name": "Zero Waste Goal",
                            "description": "Achieve zero-waste household",
                            "initiatives": [
                                {
                                    "name": "Composting Program",
                                    "description": "Compost organic waste",
                                    "systems": [
                                        {
                                            "name": "Waste Management",
                                            "kpis": [
                                                {"name": "Weekly Compost Weight", "frequency": "weekly"},
                                                {"name": "Monthly Recycling Rate", "frequency": "monthly"},
                                                {"name": "Quarterly Landfill Waste", "frequency": "quarterly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {
                    "name": "Water Conservation",
                    "description": "Reduce water usage",
                    "is_private": False,
                    "swot": {
                        "strengths": "High annual rainfall (45 inches) making rainwater collection viable. Roof area large enough for 500-gallon collection system. Low-flow showerheads and toilets already installed. Grass lawn minimal (native plants in front yard).",
                        "weaknesses": "Irrigation system lacks smart controller (waters on schedule regardless of rain). Teenagers taking long showers (20+ minutes). Washing machine old and water-inefficient. Gutter system needs repair for rainwater collection.",
                        "opportunities": "City offering rain barrel subsidy program ($75 rebate). Smart irrigation controller with weather integration available. Greywater system regulations recently relaxed. Drought-resistant landscaping rebate up to $1,500.",
                        "threats": "Water rates increasing 8% annually. Drought conditions becoming more frequent. Rain barrel mosquito issues if not maintained. Permitting requirements for greywater system unclear and potentially expensive.",
                    },
                    "challenges": [
                        {
                            "name": "Rainwater Harvesting",
                            "description": "Collect and use rainwater",
                            "initiatives": [
                                {
                                    "name": "Rainwater System",
                                    "description": "Install collection and filtration",
                                    "systems": [
                                        {
                                            "name": "Water Usage",
                                            "kpis": [
                                                {"name": "Daily Water Consumption", "frequency": "daily"},
                                                {"name": "Weekly Rainwater Collection", "frequency": "weekly"},
                                                {"name": "Monthly Water Bill", "frequency": "monthly"},
                                            ],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            ],
            "stakeholders": [
                {"name": "John Martinez", "role": "Solar Installer", "influence": 4, "interest": 4},
                {"name": "Susan Park", "role": "Environmental Consultant", "influence": 5, "interest": 5},
                {"name": "Paul Anderson", "role": "Plumber (Water Systems)", "influence": 3, "interest": 3},
                {"name": "Maria Garcia", "role": "Sustainability Coach", "influence": 4, "interest": 5},
                {"name": "Kevin O'Brien", "role": "Energy Auditor", "influence": 4, "interest": 4},
                {"name": "Linda Chen", "role": "Composting Expert", "influence": 2, "interest": 5},
                {"name": "Frank Wilson", "role": "Green Building Specialist", "influence": 3, "interest": 4},
            ],
            "stakeholder_maps": [
                {
                    "name": "Energy Transformation Team",
                    "description": "Solar and energy efficiency experts",
                    "stakeholders": ["John Martinez", "Kevin O'Brien", "Susan Park"],
                },
                {
                    "name": "Sustainability Network",
                    "description": "Overall sustainability guidance",
                    "stakeholders": ["Susan Park", "Maria Garcia", "Linda Chen", "Frank Wilson"],
                },
            ],
        },
    }

    @staticmethod
    def create_demo_organization(
        scenario_key: str,
        user_emails: list = None,
        years_of_history: int = 2,
        snapshot_frequency: str = "weekly",
    ):
        """
        Create a complete demo organization with full feature coverage.

        IMPORTANT: If an organization with the same name exists, it will be DELETED
        and recreated from scratch. This ensures a clean demo environment.

        Args:
            scenario_key: One of 'riverside_fc', 'myhealth_journey', 'green_home'
            user_emails: List of emails for demo users (default: creates 3 generic users)
            years_of_history: Number of years of historical snapshots (default: 2)
            snapshot_frequency: How often to create snapshots - 'daily', 'weekly', 'monthly' (default: 'weekly')

        Returns:
            dict: Summary of created entities
        """
        if scenario_key not in DemoDataService.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_key}. Available: {list(DemoDataService.SCENARIOS.keys())}")

        scenario = DemoDataService.SCENARIOS[scenario_key]

        # Check if organization already exists - if so, delete it completely
        existing_org = Organization.query.filter_by(name=scenario["name"]).first()
        if existing_org:
            old_org_id = existing_org.id
            # Delete organization (cascading deletes handle related entities)
            db.session.delete(existing_org)
            db.session.commit()

            # VERIFICATION: Check that cascade deletes worked
            # Query for any orphaned data that should have been deleted
            orphaned_data = []

            # Check Spaces (should be 0)
            space_count = Space.query.filter_by(organization_id=old_org_id).count()
            if space_count > 0:
                orphaned_data.append(f"Spaces: {space_count}")

            # Check Challenges (should be 0)
            challenge_count = Challenge.query.filter_by(organization_id=old_org_id).count()
            if challenge_count > 0:
                orphaned_data.append(f"Challenges: {challenge_count}")

            # Check Initiatives (should be 0)
            initiative_count = Initiative.query.filter_by(organization_id=old_org_id).count()
            if initiative_count > 0:
                orphaned_data.append(f"Initiatives: {initiative_count}")

            # Check Systems (should be 0)
            system_count = System.query.filter_by(organization_id=old_org_id).count()
            if system_count > 0:
                orphaned_data.append(f"Systems: {system_count}")

            # Check KPIs through InitiativeSystemLinks
            kpi_count = (
                db.session.query(KPI)
                .join(InitiativeSystemLink)
                .join(Initiative)
                .filter(Initiative.organization_id == old_org_id)
                .count()
            )
            if kpi_count > 0:
                orphaned_data.append(f"KPIs: {kpi_count}")

            # Check KPIValueTypeConfigs through KPIs (explicit join on kpi_id)
            config_count = (
                db.session.query(KPIValueTypeConfig)
                .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
                .join(InitiativeSystemLink)
                .join(Initiative)
                .filter(Initiative.organization_id == old_org_id)
                .count()
            )
            if config_count > 0:
                orphaned_data.append(f"KPIValueTypeConfigs: {config_count}")

            # Check Snapshots through KPIValueTypeConfigs (explicit joins)
            snapshot_count = (
                db.session.query(KPISnapshot)
                .join(KPIValueTypeConfig, KPISnapshot.kpi_value_type_config_id == KPIValueTypeConfig.id)
                .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
                .join(InitiativeSystemLink)
                .join(Initiative)
                .filter(Initiative.organization_id == old_org_id)
                .count()
            )
            if snapshot_count > 0:
                orphaned_data.append(f"Snapshots: {snapshot_count}")

            # Check Stakeholders (should be 0)
            stakeholder_count = Stakeholder.query.filter_by(organization_id=old_org_id).count()
            if stakeholder_count > 0:
                orphaned_data.append(f"Stakeholders: {stakeholder_count}")

            # Check StakeholderMaps (should be 0)
            map_count = StakeholderMap.query.filter_by(organization_id=old_org_id).count()
            if map_count > 0:
                orphaned_data.append(f"StakeholderMaps: {map_count}")

            # Check ValueTypes (should be 0)
            value_type_count = ValueType.query.filter_by(organization_id=old_org_id).count()
            if value_type_count > 0:
                orphaned_data.append(f"ValueTypes: {value_type_count}")

            # Check GovernanceBodies (should be 0)
            gb_count = GovernanceBody.query.filter_by(organization_id=old_org_id).count()
            if gb_count > 0:
                orphaned_data.append(f"GovernanceBodies: {gb_count}")

            # If any orphaned data found, raise error
            if orphaned_data:
                raise RuntimeError(
                    f"CASCADE DELETE FAILED! Orphaned data found for organization '{scenario['name']}' (ID {old_org_id}): {', '.join(orphaned_data)}"
                )

            # Log successful verification
            import logging

            logging.info(
                f"✅ CASCADE DELETE VERIFIED: All data for organization '{scenario['name']}' (ID {old_org_id}) was successfully deleted"
            )

        # Create organization with Porter's Five Forces
        org = Organization(
            name=scenario["name"],
            description=scenario["description"],
            is_active=True,
            porters_new_entrants=scenario["porters"]["new_entrants"],
            porters_suppliers=scenario["porters"]["suppliers"],
            porters_buyers=scenario["porters"]["buyers"],
            porters_substitutes=scenario["porters"]["substitutes"],
            porters_rivalry=scenario["porters"]["rivalry"],
        )
        db.session.add(org)
        db.session.flush()

        # Create demo users
        if not user_emails:
            user_emails = [
                f"demo.admin@{scenario_key}.local",
                f"demo.contributor@{scenario_key}.local",
                f"demo.viewer@{scenario_key}.local",
            ]

        # Generate unique usernames for this scenario
        role_names = ["admin", "contributor", "viewer"]

        users = []
        user_info = []  # Track user details for display
        for idx, email in enumerate(user_emails):
            # Generate unique username based on role and scenario
            role = role_names[idx] if idx < len(role_names) else f"user{idx + 1}"
            base_username = f"demo_{role}_{scenario_key}"

            # Ensure username is unique by checking DB
            username = base_username
            counter = 1
            while User.query.filter_by(login=username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            # Check if user with this email already exists
            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                # Use existing user instead of creating new one
                users.append(existing_user)
                user_info.append({"username": existing_user.login, "email": email, "role": role, "is_existing": True})
            else:
                # Create new user (Password: Demo2026! - no forced change)
                user = User(
                    login=username,
                    email=email,
                    display_name=f"Demo {role.title()}",
                    is_active=True,
                    is_global_admin=False,
                    must_change_password=False,  # No forced password change for demo users
                )
                user.set_password("Demo2026!")
                db.session.add(user)
                users.append(user)
                user_info.append({"username": username, "email": email, "role": role, "is_existing": False})
        db.session.flush()

        # Set first user as org admin if not already
        if not users[0].is_global_admin:
            users[0].is_global_admin = True

        # Check for user "moun" (dev testing user) and add them as org admin
        moun_user = User.query.filter((User.login == "moun") | (User.email.like("%moun%"))).first()
        if moun_user and (moun_user.is_super_admin or moun_user.is_global_admin):
            # Check if already a member
            from app.models import UserOrganizationMembership

            existing_membership = UserOrganizationMembership.query.filter_by(
                user_id=moun_user.id, organization_id=org.id
            ).first()

            if not existing_membership:
                # Add moun as org admin with full permissions
                membership = UserOrganizationMembership(
                    user_id=moun_user.id,
                    organization_id=org.id,
                    is_org_admin=True,
                    can_manage_spaces=True,
                    can_manage_challenges=True,
                    can_manage_initiatives=True,
                    can_manage_systems=True,
                    can_manage_kpis=True,
                    can_view_comments=True,
                    can_add_comments=True,
                )
                db.session.add(membership)
                db.session.flush()

        # Create stakeholders
        stakeholder_map_dict = {}
        for sh_data in scenario["stakeholders"]:
            stakeholder = Stakeholder(
                organization_id=org.id,
                name=sh_data["name"],
                role=sh_data["role"],
                influence_level=sh_data["influence"],
                interest_level=sh_data["interest"],
                email=f"{sh_data['name'].lower().replace(' ', '.')}@{scenario_key}.local",
                created_by_user_id=users[0].id,
            )
            db.session.add(stakeholder)
            stakeholder_map_dict[sh_data["name"]] = stakeholder
        db.session.flush()

        # Create stakeholder maps
        stakeholder_maps = []
        for map_data in scenario["stakeholder_maps"]:
            sh_map = StakeholderMap(
                organization_id=org.id,
                name=map_data["name"],
                description=map_data["description"],
                created_by_user_id=users[0].id,
            )
            db.session.add(sh_map)
            db.session.flush()
            stakeholder_maps.append(sh_map)

            # Link stakeholders to map
            for sh_name in map_data["stakeholders"]:
                stakeholder = stakeholder_map_dict[sh_name]
                membership = StakeholderMapMembership(map_id=sh_map.id, stakeholder_id=stakeholder.id)
                db.session.add(membership)

            # Create relationships within the map (random connections)
            map_stakeholders = [stakeholder_map_dict[name] for name in map_data["stakeholders"]]
            for i, source in enumerate(map_stakeholders):
                # Connect to 1-2 other stakeholders
                targets = random.sample(map_stakeholders[i + 1 :], min(2, len(map_stakeholders) - i - 1))
                for target in targets:
                    relationship_type = random.choice(
                        ["reports_to", "influences", "collaborates", "sponsors", "blocks"]
                    )
                    rel = StakeholderRelationship(
                        from_stakeholder_id=source.id,
                        to_stakeholder_id=target.id,
                        relationship_type=relationship_type,
                        strength=random.randint(3, 5),
                        notes=f"{source.name} {relationship_type.replace('_', ' ')} {target.name}",
                    )
                    db.session.add(rel)
        db.session.flush()

        # Create value types (Cost/Revenue/Net first for prominence in workspace)
        value_types = []
        value_type_configs = [
            {"name": "Cost", "kind": "numeric", "unit_label": "€"},
            {"name": "Revenue", "kind": "numeric", "unit_label": "€"},
            {"name": "Net", "kind": "numeric", "unit_label": "€"},
            {"name": "Count", "kind": "numeric", "unit_label": "units"},
            {"name": "Hours", "kind": "numeric", "unit_label": "hrs"},
            {"name": "Percentage", "kind": "numeric", "unit_label": "%"},
            {"name": "Currency", "kind": "numeric", "unit_label": "USD"},
            {"name": "Distance", "kind": "numeric", "unit_label": "km"},
            {"name": "Weight", "kind": "numeric", "unit_label": "kg"},
            {"name": "Score", "kind": "numeric", "unit_label": "pts"},
            {"name": "Rating", "kind": "numeric", "unit_label": "/5"},
        ]
        for idx, vt_data in enumerate(value_type_configs):
            vt = ValueType(
                organization_id=org.id,
                name=vt_data["name"],
                kind=vt_data["kind"],
                unit_label=vt_data["unit_label"],
                display_order=idx + 1,  # Explicit ordering
            )
            db.session.add(vt)
            value_types.append(vt)
        db.session.flush()

        # Create governance bodies for KPI oversight
        governance_bodies = []
        governance_configs = [
            {
                "name": "Executive Board",
                "abbreviation": "EXEC",
                "color": "#e74c3c",
                "description": "Strategic oversight and approval",
            },
            {
                "name": "Finance Committee",
                "abbreviation": "FIN",
                "color": "#2ecc71",
                "description": "Financial metrics and budgets",
            },
            {
                "name": "Operations Team",
                "abbreviation": "OPS",
                "color": "#3498db",
                "description": "Day-to-day operations and performance",
            },
            {
                "name": "Sustainability Council",
                "abbreviation": "SUST",
                "color": "#27ae60",
                "description": "Environmental and social impact",
            },
            {
                "name": "Quality Assurance",
                "abbreviation": "QA",
                "color": "#f39c12",
                "description": "Quality standards and compliance",
            },
        ]
        for idx, gb_data in enumerate(governance_configs):
            gb = GovernanceBody(
                organization_id=org.id,
                name=gb_data["name"],
                abbreviation=gb_data["abbreviation"],
                color=gb_data["color"],
                description=gb_data["description"],
                display_order=idx + 1,
                is_active=True,
                is_default=(idx == 0),  # First one is default
            )
            db.session.add(gb)
            governance_bodies.append(gb)
        db.session.flush()

        # Create entity hierarchy
        spaces_created = []
        challenges_created = []
        initiatives_created = []
        systems_created = []
        kpis_created = []
        configs_created = []

        for space_idx, space_data in enumerate(scenario["spaces"]):
            space = Space(
                organization_id=org.id,
                name=space_data["name"],
                description=space_data["description"],
                is_private=space_data["is_private"],
                display_order=space_idx + 1,
                created_by=users[0].id,
                swot_strengths=space_data.get("swot", {}).get("strengths"),
                swot_weaknesses=space_data.get("swot", {}).get("weaknesses"),
                swot_opportunities=space_data.get("swot", {}).get("opportunities"),
                swot_threats=space_data.get("swot", {}).get("threats"),
            )
            db.session.add(space)
            db.session.flush()
            spaces_created.append(space)

            for challenge_idx, challenge_data in enumerate(space_data["challenges"]):
                challenge = Challenge(
                    organization_id=org.id,
                    space_id=space.id,
                    name=challenge_data["name"],
                    description=challenge_data["description"],
                    display_order=challenge_idx + 1,
                )
                db.session.add(challenge)
                db.session.flush()
                challenges_created.append(challenge)

                for initiative_idx, initiative_data in enumerate(challenge_data["initiatives"]):
                    # Fill in complete initiative form with realistic data
                    initiative = Initiative(
                        organization_id=org.id,
                        name=initiative_data["name"],
                        description=initiative_data["description"],
                        mission=f"Implement {initiative_data['name']} to address {challenge_data['name']} through systematic improvements and measurable outcomes.",
                        success_criteria="Achieve target KPIs within planned timeframe. Maintain quality standards above 85%. Positive stakeholder feedback from all governance bodies.",
                        responsible_person=f"{users[0].display_name} (Lead)",
                        team_members=(
                            "\n".join([user.display_name for user in users[1:]]) + "\nExternal Consultant"
                            if len(users) > 1
                            else "External Consultant"
                        ),
                        handover_organization=f"{space_data['name']} Operations Team",
                        deliverables='[{"name": "Phase 1 Completion", "date": "Q2 2026"}, {"name": "Full Implementation", "date": "Q4 2026"}]',
                        group_label=random.choice(["A", "B", "C"]),
                        impact_on_challenge="high",
                        impact_rationale=f"Critical initiative for achieving {challenge_data['name']} objectives. Direct impact on strategic goals.",
                    )
                    db.session.add(initiative)
                    db.session.flush()
                    initiatives_created.append(initiative)

                    # Link initiative to challenge
                    link = ChallengeInitiativeLink(
                        challenge_id=challenge.id, initiative_id=initiative.id, display_order=initiative_idx + 1
                    )
                    db.session.add(link)

                    for system_idx, system_data in enumerate(initiative_data["systems"]):
                        system = System(
                            organization_id=org.id,
                            name=system_data["name"],
                            description="",
                        )
                        db.session.add(system)
                        db.session.flush()
                        systems_created.append(system)

                        # Link system to initiative
                        sys_link = InitiativeSystemLink(
                            initiative_id=initiative.id, system_id=system.id, display_order=system_idx + 1
                        )
                        db.session.add(sys_link)
                        db.session.flush()

                        # Track configs for this system (for formula setup)
                        system_configs = []

                        for kpi_idx, kpi_data in enumerate(system_data["kpis"]):
                            kpi = KPI(
                                name=kpi_data["name"],
                                initiative_system_link_id=sys_link.id,
                                display_order=kpi_idx + 1,
                            )
                            db.session.add(kpi)
                            db.session.flush()
                            kpis_created.append(kpi)

                            # Assign appropriate value type based on KPI name
                            vt = DemoDataService._select_value_type(kpi.name, value_types)

                            # Check if this is a formula KPI
                            is_formula = kpi_data.get("formula", False)

                            # Set format and scale examples based on value type
                            display_scale = None
                            display_decimals = None
                            if vt.name in ["Cost", "Revenue", "Net"]:
                                # Financial metrics: show in thousands with 1 decimal
                                display_scale = "thousands"
                                display_decimals = 1
                            elif vt.name == "Currency":
                                # Other currency: show as-is with 2 decimals
                                display_decimals = 2
                            elif vt.name in ["Count", "Score"]:
                                # Integer format - no decimals
                                display_decimals = 0

                            config = KPIValueTypeConfig(
                                kpi_id=kpi.id,
                                value_type_id=vt.id,
                                calculation_type="formula" if is_formula else "manual",
                                display_scale=display_scale,
                                display_decimals=display_decimals,
                            )
                            db.session.add(config)
                            db.session.flush()

                            # Assign governance body to KPI (distributed across different bodies)
                            if kpi_idx < len(governance_bodies):
                                gb = governance_bodies[kpi_idx % len(governance_bodies)]
                                gb_link = KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=gb.id)
                                db.session.add(gb_link)

                            # Store for formula setup
                            system_configs.append(
                                {
                                    "config": config,
                                    "kpi": kpi,
                                    "kpi_data": kpi_data,
                                    "frequency": kpi_data["frequency"],
                                    "is_formula": is_formula,
                                }
                            )

                        # Set up formula configurations for this system
                        for config_info in system_configs:
                            if config_info["is_formula"]:
                                # For Solar Economics: Net Profit = Revenue - Cost
                                if (
                                    "net" in config_info["kpi"].name.lower()
                                    or "profit" in config_info["kpi"].name.lower()
                                ):
                                    # Find Revenue and Cost configs in this system
                                    revenue_config = next(
                                        (c["config"] for c in system_configs if "revenue" in c["kpi"].name.lower()),
                                        None,
                                    )
                                    cost_config = next(
                                        (c["config"] for c in system_configs if "cost" in c["kpi"].name.lower()), None
                                    )

                                    if revenue_config and cost_config:
                                        # Set up formula: Revenue - Cost
                                        config_info["config"].calculation_config = {
                                            "operation": "subtract",
                                            "kpi_config_ids": [revenue_config.id, cost_config.id],
                                        }
                                        db.session.add(config_info["config"])

                            # Add to main configs list (skip snapshots for formulas)
                            if not config_info["is_formula"]:
                                configs_created.append(
                                    {
                                        "config": config_info["config"],
                                        "kpi": config_info["kpi"],
                                        "frequency": config_info["frequency"],
                                    }
                                )

        db.session.flush()

        # Generate historical snapshots
        snapshots_created = DemoDataService._generate_snapshots(
            configs_created, years_of_history, snapshot_frequency, users[0].id
        )

        # Create ONE contribution per KPI config to demonstrate contribution workflow
        from app.models import Contribution

        # Use the 3 demo users as contributors (cycling through them)
        contributor_names = [user.display_name for user in users[:3]]  # "Demo Admin", "Demo Contributor", "Demo Viewer"

        for idx, config_data in enumerate(configs_created):
            config = config_data["config"]
            # Get last snapshot value as base
            last_snapshot = (
                KPISnapshot.query.filter_by(kpi_value_type_config_id=config.id)
                .order_by(KPISnapshot.snapshot_date.desc())
                .first()
            )
            if last_snapshot:
                # Create one contribution with similar value (±5% variation)
                contrib_value = float(last_snapshot.consensus_value) * random.uniform(0.95, 1.05)
                # Cycle through the 3 demo users
                contributor_name = contributor_names[idx % len(contributor_names)]
                contribution = Contribution(
                    kpi_value_type_config_id=config.id,
                    contributor_name=contributor_name,
                    numeric_value=Decimal(str(round(contrib_value, 2))),
                )
                db.session.add(contribution)

        db.session.flush()

        # Create action items (mix of different states)
        action_items_created = DemoDataService._create_action_items(
            org.id, initiatives_created, kpis_created, users[0].id
        )

        db.session.commit()

        return {
            "organization": org,
            "users": users,
            "user_info": user_info,
            "stakeholders": len(stakeholder_map_dict),
            "stakeholder_maps": len(stakeholder_maps),
            "spaces": len(spaces_created),
            "challenges": len(challenges_created),
            "initiatives": len(initiatives_created),
            "systems": len(systems_created),
            "kpis": len(kpis_created),
            "configs": len(configs_created),
            "snapshots": snapshots_created,
            "action_items": action_items_created,
        }

    @staticmethod
    def _select_value_type(kpi_name: str, value_types: list):
        """Select appropriate value type based on KPI name"""
        name_lower = kpi_name.lower()
        for vt in value_types:
            # Financial value types (specific matching first)
            if vt.name == "Cost" and "cost" in name_lower:
                return vt
            if vt.name == "Revenue" and "revenue" in name_lower:
                return vt
            if vt.name == "Net" and ("net" in name_lower or "profit" in name_lower):
                return vt
            # Other value types
            if vt.name == "Hours" and ("hours" in name_lower or "time" in name_lower):
                return vt
            if vt.name == "Percentage" and ("rate" in name_lower or "satisfaction" in name_lower):
                return vt
            if vt.name == "Currency" and ("revenue" in name_lower or "bill" in name_lower or "sales" in name_lower):
                return vt
            if vt.name == "Distance" and "distance" in name_lower:
                return vt
            if vt.name == "Weight" and ("weight" in name_lower or "compost" in name_lower):
                return vt
            if vt.name == "Score" and ("score" in name_lower or "test" in name_lower):
                return vt
            if vt.name == "Rating" and "level" in name_lower:
                return vt
        # Default to Count
        return next(vt for vt in value_types if vt.name == "Count")

    @staticmethod
    def _generate_snapshots(configs, years_of_history, frequency, user_id):
        """Generate historical snapshots based on frequency"""
        today = date.today()
        start_date = today - timedelta(days=365 * years_of_history)

        snapshot_count = 0
        for config_data in configs:
            config = config_data["config"]
            kpi_frequency = config_data["frequency"]

            # Determine snapshot dates based on KPI frequency
            dates = []
            if kpi_frequency == "daily":
                current = start_date
                while current <= today:
                    dates.append(current)
                    current += timedelta(days=1)
            elif kpi_frequency == "weekly":
                current = start_date
                while current <= today:
                    dates.append(current)
                    current += timedelta(days=7)
            elif kpi_frequency == "monthly":
                current = start_date
                while current <= today:
                    dates.append(current)
                    # Move to same day next month, handle month-end edge cases
                    month = current.month + 1
                    year = current.year
                    if month > 12:
                        month = 1
                        year += 1
                    # Handle day overflow (e.g., Jan 31 -> Feb 31 doesn't exist)
                    try:
                        current = date(year, month, current.day)
                    except ValueError:
                        # Use last day of month if day doesn't exist
                        import calendar

                        last_day = calendar.monthrange(year, month)[1]
                        current = date(year, month, last_day)
            elif kpi_frequency == "quarterly":
                current = start_date
                while current <= today:
                    dates.append(current)
                    # Move 3 months ahead
                    month = current.month + 3
                    year = current.year
                    while month > 12:
                        month -= 12
                        year += 1
                    # Handle day overflow
                    try:
                        current = date(year, month, current.day)
                    except ValueError:
                        import calendar

                        last_day = calendar.monthrange(year, month)[1]
                        current = date(year, month, last_day)
            elif kpi_frequency == "yearly":
                current = start_date
                while current <= today:
                    dates.append(current)
                    # Handle leap year edge case (Feb 29)
                    try:
                        current = date(current.year + 1, current.month, current.day)
                    except ValueError:
                        # Feb 29 in non-leap year - use Feb 28
                        current = date(current.year + 1, 2, 28)
            else:
                # Default to weekly
                current = start_date
                while current <= today:
                    dates.append(current)
                    current += timedelta(days=7)

            # Generate realistic values with trend
            base_value = random.uniform(50, 500)
            trend = random.choice([-0.01, 0, 0.01, 0.02])  # -1%, 0%, +1%, +2% per snapshot

            # Generate all snapshots (historical + current) - NO contributions
            for idx, snapshot_date in enumerate(dates):
                # Apply trend
                value = base_value * (1 + trend) ** idx
                consensus_value = value * random.uniform(0.9, 1.1)  # ±10% variation

                # Create snapshot directly (fake historical data)
                snapshot = KPISnapshot(
                    kpi_value_type_config_id=config.id,
                    snapshot_date=snapshot_date,
                    year=snapshot_date.year,
                    quarter=(snapshot_date.month - 1) // 3 + 1,
                    month=snapshot_date.month,
                    snapshot_batch_id=str(uuid.uuid4()),
                    is_public=True,
                    owner_user_id=user_id,
                    consensus_status="strong",
                    consensus_value=Decimal(str(round(consensus_value, 2))),
                    contributor_count=1,
                    is_rollup_eligible=True,
                )
                db.session.add(snapshot)
                snapshot_count += 1

        return snapshot_count

    @staticmethod
    def _create_action_items(org_id, initiatives, kpis, user_id):
        """Create sample action items in various states"""
        action_items = []

        # Sample action items
        sample_actions = [
            ("Review initiative objectives", "Update and finalize initiative objectives for Q2"),
            ("Complete KPI data entry", "Enter missing KPI values for last month"),
            ("Schedule stakeholder meeting", "Arrange quarterly review with key stakeholders"),
            ("Update system documentation", "Document new processes and workflows"),
            ("Analyze performance trends", "Review KPI trends and identify improvement areas"),
            ("Prepare status report", "Create monthly status report for leadership"),
            ("Follow up on action items", "Check completion status of pending items"),
            ("Plan next sprint", "Define priorities and deliverables for next period"),
        ]

        # Create 5-10 action items
        num_items = random.randint(5, 10)
        for i in range(num_items):
            title, description = random.choice(sample_actions)
            status = random.choice(["active", "active", "completed", "draft"])  # Weight towards active
            priority = random.choice(["low", "medium", "medium", "high", "urgent"])  # Weight towards medium

            action_item = ActionItem(
                organization_id=org_id,
                type="action",
                title=title,
                description=description,
                status=status,
                priority=priority,
                owner_user_id=user_id,
                created_by_user_id=user_id,
                visibility="shared",
            )
            db.session.add(action_item)
            action_items.append(action_item)

        return len(action_items)
