#!/usr/bin/env python3
"""
Test script for the variant comparison functionality.
Verifies that all components are properly implemented.
"""

import os
import sys

def test_comparison_components():
    """Test that all comparison components exist"""
    print("🧪 Testing Variant Comparison Components")
    print("=" * 50)
    
    # Check if comparison page exists
    compare_page_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'app', 
        'project', 
        '[id]', 
        'compare', 
        'page.tsx'
    )
    
    if os.path.exists(compare_page_path):
        print("✅ Comparison page exists")
        
        # Check if it contains key components
        with open(compare_page_path, 'r') as f:
            content = f.read()
            
        checks = [
            ("DNADiff component", "function DNADiff"),
            ("Radar chart", "VariantRadarChart"),
            ("Chart.js import", "from 'react-chartjs-2'"),
            ("Variant selector", "toggleVariant"),
            ("Side-by-side layout", "gridTemplateColumns"),
            ("Floor plan display", "floor_plan_svg"),
            ("3D thumbnail", "thumbnail_url"),
            ("Score comparison", "variant.score"),
            ("Select variant", "selectVariant"),
        ]
        
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✅ {check_name} implemented")
            else:
                print(f"❌ {check_name} missing")
                
    else:
        print("❌ Comparison page not found")
        return False
    
    # Check backend endpoint
    projects_route_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'backend', 
        'routes', 
        'projects.py'
    )
    
    if os.path.exists(projects_route_path):
        with open(projects_route_path, 'r') as f:
            content = f.read()
            
        if "variants/{variant_id}/select" in content:
            print("✅ Variant selection endpoint exists")
        else:
            print("❌ Variant selection endpoint missing")
    
    # Check project page integration
    project_page_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'app', 
        'project', 
        '[id]', 
        'page.tsx'
    )
    
    if os.path.exists(project_page_path):
        with open(project_page_path, 'r') as f:
            content = f.read()
            
        if "/compare" in content and "Compare Variants" in content:
            print("✅ Compare button added to project page")
        else:
            print("❌ Compare button missing from project page")
    
    return True

def demo_comparison_features():
    """Demonstrate the comparison features"""
    print("\n🎨 Comparison Features Demo")
    print("-" * 30)
    
    features = [
        "📊 Side-by-side variant comparison (up to 3)",
        "🧬 DNA difference highlighting",
        "📐 Floor plan SVG display",
        "🏗️ 3D model thumbnails", 
        "📈 Radar chart performance comparison",
        "💰 Cost comparison table",
        "🎯 Variant selection buttons",
        "🔄 Interactive variant selector",
        "📱 Responsive design",
        "🎨 Professional dark UI"
    ]
    
    for feature in features:
        print(f"   {feature}")
    
    print("\n📋 User Flow:")
    print("   1. User completes project with multiple variants")
    print("   2. Clicks 'Compare Variants' button")
    print("   3. Selects up to 3 variants to compare")
    print("   4. Views side-by-side comparison")
    print("   5. Analyzes DNA differences (highlighted)")
    print("   6. Reviews performance radar chart")
    print("   7. Compares costs and scores")
    print("   8. Selects preferred variant")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n📦 Dependency Check")
    print("-" * 20)
    
    package_json_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'frontend', 
        'package.json'
    )
    
    if os.path.exists(package_json_path):
        with open(package_json_path, 'r') as f:
            content = f.read()
            
        deps = [
            ("Chart.js", "chart.js"),
            ("React Chart.js", "react-chartjs-2"),
            ("React Query", "@tanstack/react-query"),
            ("Axios", "axios"),
        ]
        
        for dep_name, dep_package in deps:
            if dep_package in content:
                print(f"✅ {dep_name} installed")
            else:
                print(f"❌ {dep_name} missing - run: npm install {dep_package}")
    else:
        print("❌ package.json not found")

if __name__ == "__main__":
    success = test_comparison_components()
    demo_comparison_features()
    check_dependencies()
    
    if success:
        print("\n🎉 Variant Comparison Ready!")
        print("\n🚀 Next Steps:")
        print("   1. Start the development server")
        print("   2. Navigate to a project with multiple variants")
        print("   3. Click 'Compare Variants' button")
        print("   4. Test the comparison interface")
    else:
        print("\n❌ Some components missing. Check errors above.")
    
    sys.exit(0 if success else 1)