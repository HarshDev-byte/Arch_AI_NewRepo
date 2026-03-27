#!/usr/bin/env python3
"""
Setup Supabase database for ArchAI with proper SQLAlchemy integration
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import init_db, AsyncSessionLocal, Project, DesignVariant, CostEstimate, ComplianceCheck, GeoAnalysis, AgentRun

async def setup_supabase():
    """Setup Supabase database with proper tables and demo data"""
    
    print("🔧 Setting up Supabase database with SQLAlchemy...")
    
    try:
        # Initialize database tables
        await init_db()
        print("✅ Database tables initialized!")
        
        # Check if we have existing projects
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, func
            result = await db.execute(select(func.count(Project.id)))
            project_count = result.scalar()
            
            if project_count > 0:
                print(f"📊 Found {project_count} existing projects in database")
                
                # Show existing projects
                result = await db.execute(select(Project.id, Project.name, Project.status).order_by(Project.created_at.desc()))
                projects = result.fetchall()
                for project in projects:
                    print(f"   - {project[1]} ({project[2]})")
            else:
                print("📝 No existing projects found. Creating demo projects...")
                await create_demo_projects(db)
        
        print("\n🎯 Supabase setup complete!")
        print("   - Database: Connected and ready")
        print("   - Projects: Available for testing")
        print("   - Visit http://localhost:3000 to see the projects")
        
    except Exception as e:
        print(f"❌ Error setting up Supabase: {e}")
        print("   - Check your Supabase credentials in .env")
        print("   - Ensure the database is accessible")
        print("   - Verify the DATABASE_URL is correct")

async def create_demo_projects(db):
    """Create 3 demo projects with complete data"""
    print("🏗️ Creating demo projects for ArchAI...")
    
    # Demo Project 1: Modern Villa
    project1_id = uuid.uuid4()
    project1 = Project(
        id=project1_id,
        user_id=None,  # Public demo project
        name="Modern Villa - Pune",
        status="complete",
        latitude=18.5204,
        longitude=73.8567,
        plot_area_sqm=800,
        plot_width_m=25,
        plot_depth_m=32,
        fsi_allowed=2.0,
        budget_inr=15000000,
        floors=2,
        style_preferences=["modern", "minimalist"],
        design_dna={
            "primary_style": "modern",
            "building_form": "rectangular",
            "floor_height": 3.2,
            "green_score": 78,
            "user_edited_rooms": [
                {
                    "id": "living-1",
                    "name": "Living Room",
                    "type": "living",
                    "x": 2,
                    "y": 2,
                    "w": 8,
                    "h": 6,
                    "floor": 0
                },
                {
                    "id": "kitchen-1",
                    "name": "Kitchen",
                    "type": "kitchen",
                    "x": 12,
                    "y": 2,
                    "w": 6,
                    "h": 4,
                    "floor": 0
                },
                {
                    "id": "master-1",
                    "name": "Master Bedroom",
                    "type": "master_bedroom",
                    "x": 2,
                    "y": 10,
                    "w": 7,
                    "h": 5,
                    "floor": 1
                },
                {
                    "id": "bedroom-1",
                    "name": "Bedroom 2",
                    "type": "bedroom",
                    "x": 11,
                    "y": 10,
                    "w": 6,
                    "h": 4,
                    "floor": 1
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
            "building_form": "rectangular",
            "floor_height": 3.2,
            "green_score": 78,
            "scene_graph": {"rooms": 4, "floors": 2}
        },
        score=87.5,
        is_selected=True,
        floor_plan_svg='<svg width="400" height="300"><rect x="20" y="20" width="120" height="80" fill="#E8F4FD" stroke="#185FA5"/><text x="80" y="65" text-anchor="middle" font-size="12">Living Room</text><rect x="160" y="20" width="80" height="60" fill="#FDE8E8" stroke="#993C1D"/><text x="200" y="55" text-anchor="middle" font-size="10">Kitchen</text></svg>',
        model_url="/models/demo/modern-villa.glb"
    )
    db.add(variant1)
    
    # Add cost estimate
    cost1 = CostEstimate(
        project_id=project1_id,
        breakdown={
            "structure": 4500000,
            "finishing": 3000000,
            "electrical": 1500000,
            "plumbing": 1200000,
            "miscellaneous": 4800000
        },
        total_cost_inr=15000000,
        cost_per_sqft=2800,
        roi_estimate={
            "estimated_rental_per_month": 45000,
            "resale_value_5yr": 22000000,
            "appreciation_rate_percent": 8.5
        }
    )
    db.add(cost1)
    
    # Add compliance check
    compliance1 = ComplianceCheck(
        project_id=project1_id,
        fsi_used=1.8,
        fsi_allowed=2.0,
        setback_compliance={"front": 3, "rear": 3, "sides": 1.5},
        height_compliance=True,
        parking_required=3,
        green_area_required=80,
        issues=[],
        passed=True
    )
    db.add(compliance1)
    
    # Add geo analysis
    geo1 = GeoAnalysis(
        project_id=project1_id,
        plot_data={
            "zoning": "residential",
            "road_width": 12,
            "orientation": "north_facing"
        },
        zoning_type="R1",
        fsi_allowed=2.0,
        road_access={"width": 12, "type": "paved"},
        nearby_amenities=["school", "hospital", "market"],
        solar_irradiance=5.2
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
    
    # Demo Project 2: Traditional House
    project2_id = uuid.uuid4()
    project2 = Project(
        id=project2_id,
        user_id=None,
        name="Traditional House - Mumbai",
        status="complete",
        latitude=19.0760,
        longitude=72.8777,
        plot_area_sqm=600,
        plot_width_m=20,
        plot_depth_m=30,
        fsi_allowed=1.8,
        budget_inr=12000000,
        floors=2,
        style_preferences=["traditional", "indian"],
        design_dna={
            "primary_style": "traditional",
            "building_form": "courtyard",
            "floor_height": 3.0,
            "green_score": 65,
            "user_edited_rooms": [
                {
                    "id": "living-2",
                    "name": "Living Room",
                    "type": "living",
                    "x": 3,
                    "y": 3,
                    "w": 6,
                    "h": 5,
                    "floor": 0
                },
                {
                    "id": "kitchen-2",
                    "name": "Kitchen",
                    "type": "kitchen",
                    "x": 11,
                    "y": 3,
                    "w": 5,
                    "h": 4,
                    "floor": 0
                },
                {
                    "id": "pooja-1",
                    "name": "Pooja Room",
                    "type": "pooja",
                    "x": 3,
                    "y": 10,
                    "w": 3,
                    "h": 3,
                    "floor": 0
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
            "primary_style": "traditional",
            "building_form": "courtyard",
            "floor_height": 3.0,
            "green_score": 65
        },
        score=82.3,
        is_selected=True,
        floor_plan_svg='<svg width="400" height="300"><rect x="30" y="30" width="100" height="70" fill="#E8F4FD" stroke="#185FA5"/><text x="80" y="70" text-anchor="middle" font-size="12">Living</text><rect x="150" y="30" width="80" height="60" fill="#FDE8E8" stroke="#993C1D"/><text x="190" y="65" text-anchor="middle" font-size="10">Kitchen</text><rect x="30" y="120" width="60" height="50" fill="#FDF5E8" stroke="#854F0B"/><text x="60" y="150" text-anchor="middle" font-size="10">Pooja</text></svg>',
        model_url="/models/demo/traditional-house.glb"
    )
    db.add(variant2)
    
    # Add cost estimate for project 2
    cost2 = CostEstimate(
        project_id=project2_id,
        breakdown={
            "structure": 3600000,
            "finishing": 2400000,
            "electrical": 1200000,
            "plumbing": 960000,
            "miscellaneous": 3840000
        },
        total_cost_inr=12000000,
        cost_per_sqft=3200,
        roi_estimate={
            "estimated_rental_per_month": 38000,
            "resale_value_5yr": 18000000,
            "appreciation_rate_percent": 9.2
        }
    )
    db.add(cost2)
    
    # Add compliance check for project 2
    compliance2 = ComplianceCheck(
        project_id=project2_id,
        fsi_used=1.6,
        fsi_allowed=1.8,
        setback_compliance={"front": 2.5, "rear": 2, "sides": 1},
        height_compliance=True,
        parking_required=2,
        green_area_required=60,
        issues=["Parking space insufficient"],
        passed=False
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
    
    # Demo Project 3: Contemporary Apartment
    project3_id = uuid.uuid4()
    project3 = Project(
        id=project3_id,
        user_id=None,
        name="Contemporary Apartment - Bangalore",
        status="processing",  # This one is still processing to show the progress UI
        latitude=12.9716,
        longitude=77.5946,
        plot_area_sqm=400,
        plot_width_m=16,
        plot_depth_m=25,
        fsi_allowed=2.5,
        budget_inr=8000000,
        floors=1,
        style_preferences=["contemporary", "compact"],
        design_dna={
            "primary_style": "contemporary",
            "building_form": "linear",
            "floor_height": 2.8,
            "green_score": 72
        }
    )
    db.add(project3)
    
    # Add partial agent runs for project 3 (to show processing state)
    completed_agents = ["geo", "design", "layout", "cost"]
    processing_agents = ["compliance"]
    pending_agents = ["sustainability", "threed", "vr"]
    
    for agent in completed_agents:
        run = AgentRun(
            project_id=project3_id,
            agent_name=agent,
            status="complete",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            output_data={"status": "success", "message": f"{agent} agent completed successfully"}
        )
        db.add(run)
    
    for agent in processing_agents:
        run = AgentRun(
            project_id=project3_id,
            agent_name=agent,
            status="running",
            started_at=datetime.now(),
            output_data={"status": "running", "message": f"{agent} agent is processing..."}
        )
        db.add(run)
    
    for agent in pending_agents:
        run = AgentRun(
            project_id=project3_id,
            agent_name=agent,
            status="pending",
            output_data={"status": "pending", "message": f"{agent} agent waiting to start"}
        )
        db.add(run)
    
    await db.commit()
    
    print("✅ Created 3 demo projects:")
    print(f"   1. Modern Villa - Pune (ID: {project1_id}) - COMPLETE")
    print(f"   2. Traditional House - Mumbai (ID: {project2_id}) - COMPLETE")
    print(f"   3. Contemporary Apartment - Bangalore (ID: {project3_id}) - PROCESSING")

if __name__ == "__main__":
    asyncio.run(setup_supabase())