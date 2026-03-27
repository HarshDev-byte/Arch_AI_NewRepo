#!/usr/bin/env python3
"""
Create demo projects for ArchAI showcase
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import select
from database import AsyncSessionLocal, Project, DesignVariant, CostEstimate, ComplianceCheck, GeoAnalysis, AgentRun

async def create_demo_projects():
    """Create 4 impressive demo projects for innovations competition"""
    async with AsyncSessionLocal() as db:
        print("🏗️ Creating demo projects for ArchAI Innovation Showcase...")
        
        # Demo Project 1: AI-Optimized Smart Villa
        project1_id = uuid.uuid4()
        project1 = Project(
            id=project1_id,
            user_id=None,  # Public demo project
            name="🏡 AI-Optimized Smart Villa - Pune Tech Hub",
            status="complete",
            latitude=18.5204,
            longitude=73.8567,
            plot_area_sqm=1200,
            plot_width_m=30,
            plot_depth_m=40,
            fsi_allowed=2.0,
            budget_inr=25000000,
            floors=3,
            style_preferences=["modern", "smart-home", "sustainable"],
            design_dna={
                "primary_style": "modern",
                "building_form": "L-shaped",
                "floor_height": 3.5,
                "green_score": 92,
                "smart_features": ["IoT integration", "solar panels", "rainwater harvesting", "smart lighting"],
                "sustainability_rating": "LEED Platinum",
                "user_edited_rooms": [
                    {
                        "id": "living-1",
                        "name": "Smart Living Room",
                        "type": "living",
                        "x": 2,
                        "y": 2,
                        "w": 10,
                        "h": 8,
                        "floor": 0,
                        "features": ["voice control", "automated blinds", "climate control"]
                    },
                    {
                        "id": "kitchen-1",
                        "name": "AI Kitchen",
                        "type": "kitchen",
                        "x": 14,
                        "y": 2,
                        "w": 8,
                        "h": 6,
                        "floor": 0,
                        "features": ["smart appliances", "inventory tracking", "meal planning AI"]
                    },
                    {
                        "id": "office-1",
                        "name": "Home Office",
                        "type": "office",
                        "x": 2,
                        "y": 12,
                        "w": 6,
                        "h": 5,
                        "floor": 1,
                        "features": ["soundproofing", "ergonomic lighting", "video conferencing setup"]
                    },
                    {
                        "id": "master-1",
                        "name": "Master Suite",
                        "type": "master_bedroom",
                        "x": 10,
                        "y": 12,
                        "w": 9,
                        "h": 7,
                        "floor": 1,
                        "features": ["smart bed", "automated curtains", "air purification"]
                    },
                    {
                        "id": "gym-1",
                        "name": "Smart Gym",
                        "type": "gym",
                        "x": 2,
                        "y": 2,
                        "w": 8,
                        "h": 6,
                        "floor": 2,
                        "features": ["AI fitness tracking", "virtual trainer", "health monitoring"]
                    },
                    {
                        "id": "terrace-1",
                        "name": "Rooftop Garden",
                        "type": "terrace",
                        "x": 12,
                        "y": 2,
                        "w": 10,
                        "h": 8,
                        "floor": 2,
                        "features": ["automated irrigation", "solar panels", "urban farming"]
                    }
                ]
            }
        )
        db.add(project1)
        
        # Add design variant for project 1
        variant1 = DesignVariant(
            project_id=project1_id,
            variant_number=1,
            dna={
                "primary_style": "modern",
                "building_form": "L-shaped",
                "floor_height": 3.5,
                "green_score": 92,
                "smart_features": ["IoT integration", "solar panels", "rainwater harvesting"],
                "scene_graph": {"rooms": 6, "floors": 3, "smart_devices": 45}
            },
            score=94.8,
            is_selected=True,
            floor_plan_svg='<svg width="500" height="400"><rect x="20" y="20" width="160" height="120" fill="#E8F4FD" stroke="#185FA5" stroke-width="2"/><text x="100" y="85" text-anchor="middle" font-size="14" font-weight="bold">Smart Living Room</text><rect x="200" y="20" width="120" height="90" fill="#FDE8E8" stroke="#993C1D" stroke-width="2"/><text x="260" y="70" text-anchor="middle" font-size="12">AI Kitchen</text><rect x="20" y="160" width="90" height="75" fill="#E8F5E8" stroke="#2D5A2D" stroke-width="2"/><text x="65" y="200" text-anchor="middle" font-size="11">Home Office</text><rect x="130" y="160" width="135" height="105" fill="#F0E8FF" stroke="#6B2C91" stroke-width="2"/><text x="197" y="215" text-anchor="middle" font-size="12">Master Suite</text><rect x="20" y="260" width="120" height="90" fill="#FFF8E8" stroke="#B8860B" stroke-width="2"/><text x="80" y="310" text-anchor="middle" font-size="12">Smart Gym</text><rect x="160" y="260" width="150" height="120" fill="#E8FFE8" stroke="#228B22" stroke-width="2"/><text x="235" y="325" text-anchor="middle" font-size="12">Rooftop Garden</text></svg>',
            model_url="/models/demo/smart-villa.glb"
        )
        db.add(variant1)
        
        # Add cost estimate
        cost1 = CostEstimate(
            project_id=project1_id,
            breakdown={
                "structure": 8000000,
                "finishing": 6000000,
                "smart_systems": 4000000,
                "electrical": 2500000,
                "plumbing": 1800000,
                "solar_installation": 1200000,
                "miscellaneous": 1500000
            },
            total_cost_inr=25000000,
            cost_per_sqft=3200,
            roi_estimate={
                "estimated_rental_per_month": 75000,
                "resale_value_5yr": 38000000,
                "appreciation_rate_percent": 12.5,
                "energy_savings_per_year": 180000,
                "smart_home_premium": 15
            }
        )
        db.add(cost1)
        
        # Add compliance check
        compliance1 = ComplianceCheck(
            project_id=project1_id,
            fsi_used=1.9,
            fsi_allowed=2.0,
            setback_compliance={"front": 4, "rear": 4, "sides": 2},
            height_compliance=True,
            parking_required=4,
            green_area_required=120,
            issues=[],
            passed=True
        )
        db.add(compliance1)
        
        # Add geo analysis
        geo1 = GeoAnalysis(
            project_id=project1_id,
            plot_data={
                "zoning": "residential_premium",
                "road_width": 18,
                "orientation": "north_east_facing",
                "soil_type": "black_cotton",
                "water_table": 15
            },
            zoning_type="R1-Premium",
            fsi_allowed=2.0,
            road_access=True,
            nearby_amenities=["tech_park", "international_school", "hospital", "mall", "metro_station"],
            solar_irradiance=5.8,
            wind_patterns={"prevailing": "south_west", "speed": 12}
        )
        db.add(geo1)
        
        # Add agent runs for project 1
        agents = ["geo", "design", "layout", "cost", "compliance", "sustainability", "threed", "vr"]
        for agent in agents:
            run = AgentRun(
                project_id=project1_id,
                agent_name=agent,
                status="complete",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output_data={"status": "success", "message": f"{agent} agent completed successfully"}
            )
            db.add(run)
        
        # Demo Project 2: Sustainable Co-living Complex
        project2_id = uuid.uuid4()
        project2 = Project(
            id=project2_id,
            user_id=None,
            name="🌱 Sustainable Co-living Complex - Goa Eco-Zone",
            status="complete",
            latitude=15.2993,
            longitude=74.1240,
            plot_area_sqm=2000,
            plot_width_m=40,
            plot_depth_m=50,
            fsi_allowed=1.5,
            budget_inr=35000000,
            floors=2,
            style_preferences=["sustainable", "tropical", "co-living"],
            design_dna={
                "primary_style": "tropical_modern",
                "building_form": "courtyard_cluster",
                "floor_height": 3.2,
                "green_score": 96,
                "sustainability_features": ["bamboo structure", "natural ventilation", "greywater recycling", "organic gardens"],
                "community_spaces": ["co-working", "shared kitchen", "meditation garden", "skill exchange hub"],
                "user_edited_rooms": [
                    {
                        "id": "cowork-1",
                        "name": "Co-working Hub",
                        "type": "coworking",
                        "x": 5,
                        "y": 5,
                        "w": 12,
                        "h": 8,
                        "floor": 0,
                        "features": ["high-speed internet", "flexible seating", "video conferencing", "quiet zones"]
                    },
                    {
                        "id": "kitchen-2",
                        "name": "Community Kitchen",
                        "type": "shared_kitchen",
                        "x": 20,
                        "y": 5,
                        "w": 10,
                        "h": 6,
                        "floor": 0,
                        "features": ["commercial grade", "meal planning system", "herb garden", "composting"]
                    },
                    {
                        "id": "living-2",
                        "name": "Community Lounge",
                        "type": "community_living",
                        "x": 5,
                        "y": 15,
                        "w": 15,
                        "h": 10,
                        "floor": 0,
                        "features": ["flexible furniture", "entertainment system", "library corner", "game area"]
                    },
                    {
                        "id": "pod-1",
                        "name": "Living Pod 1",
                        "type": "micro_unit",
                        "x": 5,
                        "y": 5,
                        "w": 4,
                        "h": 6,
                        "floor": 1,
                        "features": ["murphy bed", "compact storage", "private balcony", "smart controls"]
                    },
                    {
                        "id": "pod-2",
                        "name": "Living Pod 2",
                        "type": "micro_unit",
                        "x": 11,
                        "y": 5,
                        "w": 4,
                        "h": 6,
                        "floor": 1,
                        "features": ["murphy bed", "compact storage", "private balcony", "smart controls"]
                    },
                    {
                        "id": "garden-1",
                        "name": "Meditation Garden",
                        "type": "garden",
                        "x": 25,
                        "y": 15,
                        "w": 10,
                        "h": 12,
                        "floor": 0,
                        "features": ["water feature", "native plants", "seating areas", "yoga deck"]
                    }
                ]
            }
        )
        db.add(project2)
        
        # Add design variant for project 2
        variant2 = DesignVariant(
            project_id=project2_id,
            variant_number=1,
            dna={
                "primary_style": "tropical_modern",
                "building_form": "courtyard_cluster",
                "floor_height": 3.2,
                "green_score": 96,
                "sustainability_rating": "Net Zero Energy",
                "community_integration": 95
            },
            score=93.7,
            is_selected=True,
            floor_plan_svg='<svg width="600" height="500"><rect x="50" y="50" width="180" height="120" fill="#E8F4FD" stroke="#185FA5" stroke-width="2"/><text x="140" y="115" text-anchor="middle" font-size="14" font-weight="bold">Co-working Hub</text><rect x="250" y="50" width="150" height="90" fill="#FDE8E8" stroke="#993C1D" stroke-width="2"/><text x="325" y="100" text-anchor="middle" font-size="12">Community Kitchen</text><rect x="50" y="190" width="225" height="150" fill="#E8F5E8" stroke="#2D5A2D" stroke-width="2"/><text x="162" y="270" text-anchor="middle" font-size="14">Community Lounge</text><rect x="300" y="190" width="60" height="90" fill="#F0E8FF" stroke="#6B2C91" stroke-width="2"/><text x="330" y="240" text-anchor="middle" font-size="10">Pod 1</text><rect x="380" y="190" width="60" height="90" fill="#F0E8FF" stroke="#6B2C91" stroke-width="2"/><text x="410" y="240" text-anchor="middle" font-size="10">Pod 2</text><rect x="300" y="300" width="150" height="180" fill="#E8FFE8" stroke="#228B22" stroke-width="2"/><text x="375" y="395" text-anchor="middle" font-size="12">Meditation Garden</text></svg>',
            model_url="/models/demo/sustainable-coliving.glb"
        )
        db.add(variant2)
        
        # Add cost estimate for project 2
        cost2 = CostEstimate(
            project_id=project2_id,
            breakdown={
                "sustainable_structure": 12000000,
                "eco_finishing": 8000000,
                "renewable_energy": 5000000,
                "water_systems": 3000000,
                "smart_systems": 4000000,
                "landscaping": 2000000,
                "miscellaneous": 1000000
            },
            total_cost_inr=35000000,
            cost_per_sqft=2800,
            roi_estimate={
                "estimated_rental_per_month": 120000,
                "resale_value_5yr": 55000000,
                "appreciation_rate_percent": 11.8,
                "operational_savings_per_year": 420000,
                "carbon_credits_value": 50000
            }
        )
        db.add(cost2)
        
        # Add compliance check for project 2
        compliance2 = ComplianceCheck(
            project_id=project2_id,
            fsi_used=1.4,
            fsi_allowed=1.5,
            setback_compliance={"front": 5, "rear": 6, "sides": 3},
            height_compliance=True,
            parking_required=8,
            green_area_required=200,
            issues=[],
            passed=True
        )
        db.add(compliance2)
        
        # Add agent runs for project 2
        for agent in agents:
            run = AgentRun(
                project_id=project2_id,
                agent_name=agent,
                status="complete",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output_data={"status": "success", "message": f"{agent} agent completed successfully"}
            )
            db.add(run)
        
        # Add geo analysis for project 2
        geo2 = GeoAnalysis(
            project_id=project2_id,
            plot_data={
                "zoning": "eco_residential",
                "road_width": 15,
                "orientation": "south_west_facing",
                "soil_type": "laterite",
                "water_table": 8,
                "coastal_proximity": 2.5
            },
            zoning_type="ECO-R1",
            fsi_allowed=1.5,
            road_access=True,
            nearby_amenities=["beach", "organic_market", "yoga_center", "art_gallery", "co-working_spaces"],
            solar_irradiance=6.2,
            wind_patterns={"prevailing": "south_west", "speed": 18},
            environmental_factors={"monsoon_intensity": "high", "humidity": 75, "temperature_range": "24-32°C"}
        )
        db.add(geo2)
        
        # Demo Project 3: Affordable Housing Innovation
        project3_id = uuid.uuid4()
        project3 = Project(
            id=project3_id,
            user_id=None,
            name="🏘️ Affordable Housing Innovation - Delhi NCR",
            status="complete",
            latitude=28.7041,
            longitude=77.1025,
            plot_area_sqm=5000,
            plot_width_m=50,
            plot_depth_m=100,
            fsi_allowed=3.0,
            budget_inr=80000000,
            floors=4,
            style_preferences=["affordable", "modular", "community-focused"],
            design_dna={
                "primary_style": "modular_affordable",
                "building_form": "linear_blocks",
                "floor_height": 2.7,
                "green_score": 78,
                "affordability_features": ["prefab construction", "shared amenities", "energy efficiency", "low maintenance"],
                "community_features": ["skill center", "daycare", "health clinic", "community hall"],
                "user_edited_rooms": [
                    {
                        "id": "unit-1",
                        "name": "1BHK Unit Type A",
                        "type": "affordable_1bhk",
                        "x": 2,
                        "y": 2,
                        "w": 6,
                        "h": 8,
                        "floor": 0,
                        "features": ["modular kitchen", "multipurpose living", "efficient storage", "natural lighting"]
                    },
                    {
                        "id": "unit-2",
                        "name": "2BHK Unit Type B",
                        "type": "affordable_2bhk",
                        "x": 10,
                        "y": 2,
                        "w": 8,
                        "h": 10,
                        "floor": 0,
                        "features": ["flexible partitions", "dual-purpose rooms", "compact design", "cross ventilation"]
                    },
                    {
                        "id": "community-1",
                        "name": "Community Center",
                        "type": "community_hall",
                        "x": 20,
                        "y": 2,
                        "w": 12,
                        "h": 8,
                        "floor": 0,
                        "features": ["multipurpose hall", "meeting rooms", "library", "computer center"]
                    },
                    {
                        "id": "skill-1",
                        "name": "Skill Development Center",
                        "type": "skill_center",
                        "x": 35,
                        "y": 2,
                        "w": 10,
                        "h": 6,
                        "floor": 0,
                        "features": ["training rooms", "workshop space", "digital literacy", "entrepreneurship hub"]
                    },
                    {
                        "id": "health-1",
                        "name": "Primary Health Center",
                        "type": "health_clinic",
                        "x": 35,
                        "y": 10,
                        "w": 8,
                        "h": 5,
                        "floor": 0,
                        "features": ["consultation rooms", "pharmacy", "telemedicine", "maternal care"]
                    }
                ]
            }
        )
        db.add(project3)
        
        # Add design variant for project 3
        variant3 = DesignVariant(
            project_id=project3_id,
            variant_number=1,
            dna={
                "primary_style": "modular_affordable",
                "building_form": "linear_blocks",
                "floor_height": 2.7,
                "green_score": 78,
                "affordability_score": 92,
                "community_integration": 88
            },
            score=89.2,
            is_selected=True,
            floor_plan_svg='<svg width="700" height="400"><rect x="20" y="20" width="90" height="120" fill="#E8F4FD" stroke="#185FA5" stroke-width="2"/><text x="65" y="85" text-anchor="middle" font-size="11">1BHK Type A</text><rect x="130" y="20" width="120" height="150" fill="#FDE8E8" stroke="#993C1D" stroke-width="2"/><text x="190" y="100" text-anchor="middle" font-size="11">2BHK Type B</text><rect x="270" y="20" width="180" height="120" fill="#E8F5E8" stroke="#2D5A2D" stroke-width="2"/><text x="360" y="85" text-anchor="middle" font-size="12">Community Center</text><rect x="470" y="20" width="150" height="90" fill="#F0E8FF" stroke="#6B2C91" stroke-width="2"/><text x="545" y="70" text-anchor="middle" font-size="11">Skill Center</text><rect x="470" y="130" width="120" height="75" fill="#FFF8E8" stroke="#B8860B" stroke-width="2"/><text x="530" y="172" text-anchor="middle" font-size="11">Health Center</text></svg>',
            model_url="/models/demo/affordable-housing.glb"
        )
        db.add(variant3)
        
        # Add cost estimate for project 3
        cost3 = CostEstimate(
            project_id=project3_id,
            breakdown={
                "prefab_structure": 32000000,
                "basic_finishing": 16000000,
                "utilities": 12000000,
                "community_facilities": 8000000,
                "infrastructure": 6000000,
                "landscaping": 3000000,
                "miscellaneous": 3000000
            },
            total_cost_inr=80000000,
            cost_per_sqft=1600,
            roi_estimate={
                "estimated_rental_per_month": 280000,
                "resale_value_5yr": 120000000,
                "appreciation_rate_percent": 8.5,
                "social_impact_score": 95,
                "government_subsidies": 12000000
            }
        )
        db.add(cost3)
        
        # Add compliance check for project 3
        compliance3 = ComplianceCheck(
            project_id=project3_id,
            fsi_used=2.8,
            fsi_allowed=3.0,
            setback_compliance={"front": 6, "rear": 6, "sides": 3},
            height_compliance=True,
            parking_required=40,
            green_area_required=500,
            issues=[],
            passed=True
        )
        db.add(compliance3)
        
        # Add geo analysis for project 3
        geo3 = GeoAnalysis(
            project_id=project3_id,
            plot_data={
                "zoning": "affordable_residential",
                "road_width": 24,
                "orientation": "north_facing",
                "soil_type": "alluvial",
                "water_table": 12,
                "metro_connectivity": True
            },
            zoning_type="AR-3",
            fsi_allowed=3.0,
            road_access=True,
            nearby_amenities=["metro_station", "government_school", "primary_health_center", "market", "bus_depot"],
            solar_irradiance=5.5,
            wind_patterns={"prevailing": "north_west", "speed": 8},
            infrastructure={"water_supply": "24x7", "electricity": "reliable", "sewage": "connected", "internet": "fiber"}
        )
        db.add(geo3)
        
        # Demo Project 4: Mixed-Use Innovation Hub
        project4_id = uuid.uuid4()
        project4 = Project(
            id=project4_id,
            user_id=None,
            name="🏢 Mixed-Use Innovation Hub - Hyderabad HITEC City",
            status="processing",  # This one is still processing to show the progress UI
            latitude=17.4435,
            longitude=78.3772,
            plot_area_sqm=3000,
            plot_width_m=50,
            plot_depth_m=60,
            fsi_allowed=4.0,
            budget_inr=120000000,
            floors=8,
            style_preferences=["contemporary", "mixed-use", "tech-hub"],
            design_dna={
                "primary_style": "contemporary_commercial",
                "building_form": "tower_with_podium",
                "floor_height": 3.6,
                "green_score": 85,
                "innovation_features": ["flexible workspaces", "startup incubator", "event spaces", "retail integration"],
                "tech_features": ["5G ready", "IoT infrastructure", "smart building systems", "EV charging"],
                "user_edited_rooms": [
                    {
                        "id": "retail-1",
                        "name": "Ground Floor Retail",
                        "type": "retail",
                        "x": 2,
                        "y": 2,
                        "w": 20,
                        "h": 8,
                        "floor": 0,
                        "features": ["flexible layouts", "high ceilings", "street access", "digital displays"]
                    },
                    {
                        "id": "cowork-2",
                        "name": "Co-working Floors",
                        "type": "coworking",
                        "x": 2,
                        "y": 2,
                        "w": 25,
                        "h": 15,
                        "floor": 2,
                        "features": ["hot desks", "private offices", "meeting rooms", "collaboration zones"]
                    },
                    {
                        "id": "incubator-1",
                        "name": "Startup Incubator",
                        "type": "incubator",
                        "x": 2,
                        "y": 2,
                        "w": 25,
                        "h": 15,
                        "floor": 4,
                        "features": ["mentorship rooms", "pitch areas", "prototype lab", "networking lounge"]
                    },
                    {
                        "id": "event-1",
                        "name": "Event & Conference",
                        "type": "event_space",
                        "x": 2,
                        "y": 2,
                        "w": 25,
                        "h": 15,
                        "floor": 6,
                        "features": ["auditorium", "breakout rooms", "exhibition space", "broadcast facility"]
                    },
                    {
                        "id": "terrace-2",
                        "name": "Sky Lounge",
                        "type": "sky_lounge",
                        "x": 2,
                        "y": 2,
                        "w": 25,
                        "h": 15,
                        "floor": 7,
                        "features": ["panoramic views", "outdoor seating", "bar area", "event hosting"]
                    }
                ]
            }
        )
        db.add(project4)
        
        # Add design variant for project 4
        variant4 = DesignVariant(
            project_id=project4_id,
            variant_number=1,
            dna={
                "primary_style": "contemporary_commercial",
                "building_form": "tower_with_podium",
                "floor_height": 3.6,
                "green_score": 85,
                "innovation_score": 94,
                "tech_integration": 96
            },
            score=91.5,
            is_selected=True,
            floor_plan_svg='<svg width="600" height="600"><rect x="20" y="20" width="300" height="120" fill="#E8F4FD" stroke="#185FA5" stroke-width="2"/><text x="170" y="85" text-anchor="middle" font-size="14" font-weight="bold">Ground Floor Retail</text><rect x="20" y="160" width="375" height="225" fill="#FDE8E8" stroke="#993C1D" stroke-width="2"/><text x="207" y="280" text-anchor="middle" font-size="16">Co-working Floors</text><rect x="20" y="400" width="375" height="225" fill="#E8F5E8" stroke="#2D5A2D" stroke-width="2"/><text x="207" y="520" text-anchor="middle" font-size="16">Startup Incubator</text><rect x="420" y="160" width="160" height="180" fill="#F0E8FF" stroke="#6B2C91" stroke-width="2"/><text x="500" y="255" text-anchor="middle" font-size="12">Event Space</text><rect x="420" y="360" width="160" height="120" fill="#FFF8E8" stroke="#B8860B" stroke-width="2"/><text x="500" y="425" text-anchor="middle" font-size="12">Sky Lounge</text></svg>',
            model_url="/models/demo/innovation-hub.glb"
        )
        db.add(variant4)
        
        # Add cost estimate for project 4
        cost4 = CostEstimate(
            project_id=project4_id,
            breakdown={
                "structure": 48000000,
                "commercial_finishing": 24000000,
                "tech_infrastructure": 18000000,
                "elevators_mep": 12000000,
                "smart_systems": 8000000,
                "retail_fitout": 6000000,
                "miscellaneous": 4000000
            },
            total_cost_inr=120000000,
            cost_per_sqft=4000,
            roi_estimate={
                "estimated_rental_per_month": 450000,
                "resale_value_5yr": 180000000,
                "appreciation_rate_percent": 10.5,
                "commercial_premium": 25,
                "tech_hub_bonus": 15
            }
        )
        db.add(cost4)
        
        # Add compliance check for project 4
        compliance4 = ComplianceCheck(
            project_id=project4_id,
            fsi_used=3.8,
            fsi_allowed=4.0,
            setback_compliance={"front": 8, "rear": 6, "sides": 4},
            height_compliance=True,
            parking_required=60,
            green_area_required=300,
            issues=[],
            passed=True,
            certifications=["IGBC Platinum", "LEED Gold", "Smart Building Certified", "Fire Safety NOC"]
        )
        db.add(compliance4)
        
        # Add geo analysis for project 4
        geo4 = GeoAnalysis(
            project_id=project4_id,
            plot_data={
                "zoning": "commercial_mixed_use",
                "road_width": 30,
                "orientation": "east_facing",
                "soil_type": "hard_rock",
                "water_table": 25,
                "metro_connectivity": True
            },
            zoning_type="CMU-4",
            fsi_allowed=4.0,
            road_access=True,
            nearby_amenities=["tech_companies", "metro_station", "international_airport", "business_hotels", "convention_center"],
            solar_irradiance=5.8,
            wind_patterns={"prevailing": "south_east", "speed": 14},
            infrastructure={"fiber_optic": "dedicated", "power_backup": "100%", "water_supply": "dual_source", "waste_management": "automated"}
        )
        db.add(geo4)
        
        # Add agent runs for all completed projects
        agents = ["geo", "design", "layout", "cost", "compliance", "sustainability", "threed", "vr"]
        
        # Project 1 - All agents complete
        for agent in agents:
            run = AgentRun(
                project_id=project1_id,
                agent_name=agent,
                status="complete",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output_data={
                    "status": "success", 
                    "message": f"{agent} agent completed successfully",
                    "metrics": {"processing_time": f"{agent}_time", "confidence": 0.95}
                }
            )
            db.add(run)
        
        # Project 2 - All agents complete (already added above)
        
        # Project 3 - All agents complete
        for agent in agents:
            run = AgentRun(
                project_id=project3_id,
                agent_name=agent,
                status="complete",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output_data={
                    "status": "success", 
                    "message": f"{agent} agent completed successfully",
                    "metrics": {"processing_time": f"{agent}_time", "confidence": 0.89}
                }
            )
            db.add(run)
        
        # Project 4 - Partial completion to show processing state
        completed_agents_p4 = ["geo", "design", "layout", "cost", "compliance"]
        processing_agents_p4 = ["sustainability"]
        pending_agents_p4 = ["threed", "vr"]
        
        for agent in completed_agents_p4:
            run = AgentRun(
                project_id=project4_id,
                agent_name=agent,
                status="complete",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                output_data={
                    "status": "success", 
                    "message": f"{agent} agent completed successfully",
                    "metrics": {"processing_time": f"{agent}_time", "confidence": 0.91}
                }
            )
            db.add(run)
        
        for agent in processing_agents_p4:
            run = AgentRun(
                project_id=project4_id,
                agent_name=agent,
                status="running",
                started_at=datetime.now(),
                output_data={
                    "status": "running", 
                    "message": f"{agent} agent is analyzing sustainability metrics...",
                    "progress": 65
                }
            )
            db.add(run)
        
        for agent in pending_agents_p4:
            run = AgentRun(
                project_id=project4_id,
                agent_name=agent,
                status="pending",
                output_data={
                    "status": "pending", 
                    "message": f"{agent} agent waiting to start",
                    "queue_position": pending_agents_p4.index(agent) + 1
                }
            )
            db.add(run)
        
        await db.commit()
        
        print("🚀 Created 4 IMPRESSIVE demo projects for Innovation Competition:")
        print(f"   1. 🏡 AI-Optimized Smart Villa - Pune Tech Hub (ID: {project1_id}) - COMPLETE")
        print(f"      • LEED Platinum • Smart Home Tech • 92% Green Score • ₹2.5Cr")
        print(f"   2. 🌱 Sustainable Co-living Complex - Goa Eco-Zone (ID: {project2_id}) - COMPLETE") 
        print(f"      • Net Zero Energy • Community Living • 96% Green Score • ₹3.5Cr")
        print(f"   3. 🏘️ Affordable Housing Innovation - Delhi NCR (ID: {project3_id}) - COMPLETE")
        print(f"      • PMAY Compliant • Modular Construction • Social Impact • ₹8Cr")
        print(f"   4. 🏢 Mixed-Use Innovation Hub - Hyderabad HITEC City (ID: {project4_id}) - PROCESSING")
        print(f"      • Tech Hub • Startup Incubator • Smart Building • ₹12Cr")
        print("\n🎯 INNOVATION SHOWCASE READY!")
        print("   ✨ Diverse project types showcasing AI capabilities")
        print("   🏆 Competition-ready with impressive metrics & features")
        print("   🎨 Rich visualizations and detailed floor plans")
        print("   📊 Complete cost analysis and ROI projections")
        print("   🌍 Sustainability and compliance certifications")
        print("   🤖 AI agent orchestration demonstrations")
        print("\n🌐 Access: http://localhost:3000")
        print("   • Explore each project's unique features")
        print("   • Test AI Floor Plan Editor capabilities") 
        print("   • Demonstrate MCP integration")
        print("   • Show real-time agent processing")

if __name__ == "__main__":
    asyncio.run(create_demo_projects())