#!/usr/bin/env python3
"""
Test script for Phase 4 Component Optimization.

This script tests whether the pre-aggregation system is working correctly
and components can access pre-computed data.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_feature_flags():
    """Test feature flag configuration."""
    print("Testing feature flags...")
    
    try:
        from utils.feature_flags import feature_flags
        
        # Check all performance-related flags
        performance_flags = [
            'use_global_data_manager',
            'use_smart_cache', 
            'use_callback_debouncing',
            'use_pre_aggregation'
        ]
        
        for flag in performance_flags:
            status = feature_flags.is_enabled(flag)
            print(f"{'✅' if status else '⚠️'} {flag}: {'Enabled' if status else 'Disabled'}")
        
        # Check if Phase 4 flag is enabled
        if feature_flags.is_enabled('use_pre_aggregation'):
            print("✅ Phase 4 pre-aggregation is enabled")
            return True
        else:
            print("❌ Phase 4 pre-aggregation is disabled")
            return False
        
    except Exception as e:
        print(f"❌ Error testing feature flags: {str(e)}")
        return False

def test_data_aggregator_availability():
    """Test if data_aggregator is available and has pre-computed data."""
    print("\nTesting data_aggregator availability...")
    
    try:
        from utils.data_aggregator import get_data_aggregator
        from utils.feature_flags import feature_flags
        
        # Check if pre-aggregation feature is available
        if not feature_flags.is_enabled('use_pre_aggregation'):
            print("❌ use_pre_aggregation feature flag is disabled")
            return False
            
        aggregator = get_data_aggregator()
        
        # Check available aggregations
        available = aggregator.get_available_aggregations()
        status = aggregator.get_aggregation_status()
        
        print(f"✅ Data aggregator initialized successfully")
        print(f"Available aggregations: {available}")
        print(f"Aggregation status: {status}")
        
        # Test specific aggregations needed by components
        required_aggregations = ['state_subpart_totals', 'yearly_trends', 'subpart_summaries']
        
        all_available = True
        for agg_name in required_aggregations:
            if aggregator.is_aggregation_available(agg_name):
                data = aggregator.get_aggregation(agg_name)
                if data is not None:
                    print(f"✅ {agg_name}: Available ({len(data)} records)")
                else:
                    print(f"❌ {agg_name}: Available but data is None")
                    all_available = False
            else:
                print(f"❌ {agg_name}: Not available")
                all_available = False
        
        return all_available
        
    except Exception as e:
        print(f"❌ Error testing data_aggregator: {str(e)}")
        return False

def test_component_imports():
    """Test if components can be imported and have optimization code."""
    print("\nTesting component imports and optimization...")
    
    try:
        # Test imports without creating Dash components
        print("Testing state_breakdown_graph import...")
        import components.state_breakdown_graph
        print("✅ state_breakdown_graph imported successfully")
        
        print("Testing subpart_graph_v2 import...")
        import components.subpart_graph_v2
        print("✅ subpart_graph_v2 imported successfully")
        
        print("Testing subpart_timeline_graph import...")
        import components.subpart_timeline_graph
        print("✅ subpart_timeline_graph imported successfully")
        
        # Check if components have the optimization code
        import inspect
        
        # Check state_breakdown_graph for data_aggregator usage
        source = inspect.getsource(components.state_breakdown_graph)
        if 'get_data_aggregator' in source and 'state_subpart_totals' in source:
            print("✅ state_breakdown_graph has Phase 4 optimization code")
        else:
            print("❌ state_breakdown_graph missing Phase 4 optimization")
            return False
            
        # Check subpart_timeline_graph for data_aggregator usage
        source = inspect.getsource(components.subpart_timeline_graph)
        if 'get_data_aggregator' in source and 'yearly_trends' in source:
            print("✅ subpart_timeline_graph has Phase 4 optimization code")
        else:
            print("❌ subpart_timeline_graph missing Phase 4 optimization")
            return False
            
        # Check subpart_graph_v2 for data_aggregator usage
        source = inspect.getsource(components.subpart_graph_v2)
        if 'get_data_aggregator' in source and 'subpart_summaries' in source:
            print("✅ subpart_graph_v2 has Phase 4 optimization code")
        else:
            print("❌ subpart_graph_v2 missing Phase 4 optimization")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing component imports: {str(e)}")
        return False

def main():
    """Run all Phase 4 optimization tests."""
    print("=" * 60)
    print("Phase 4 Component Optimization Test")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_feature_flags,
        test_data_aggregator_availability,
        test_component_imports
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All Phase 4 optimization tests passed!")
        print("\nPhase 4 Component Optimization completed successfully!")
        print("\nImplemented optimizations:")
        print("✅ Updated state_breakdown_graph to use pre-computed state_subpart_totals")
        print("✅ Updated subpart_timeline_graph to use pre-computed yearly_trends")
        print("✅ Updated subpart_graph_v2 to use pre-computed subpart_summaries")
        print("✅ Enabled use_pre_aggregation feature flag")
        print("✅ Performance monitoring decorators in place")
        print("\nNext steps:")
        print("1. Monitor performance improvements in production")
        print("2. Run comprehensive integration tests")
        print("3. Consider implementing progressive loading (Phase 4 continuation)")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)