#!/usr/bin/env python3
"""
Test script to verify data aggregator initialization and pre-computation.

This script tests the complete initialization flow including data loading
and aggregation pre-computation as it would happen in the main application.
"""

import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_aggregation_initialization():
    """Test the complete aggregation initialization process."""
    print("=" * 70)
    print("Testing Data Aggregator Initialization")
    print("=" * 70)
    
    try:
        # Test 1: Feature flags
        print("\n1. Testing feature flags...")
        from utils.feature_flags import feature_flags
        
        required_flags = {
            'use_global_data_manager': feature_flags.is_enabled('use_global_data_manager'),
            'use_pre_aggregation': feature_flags.is_enabled('use_pre_aggregation')
        }
        
        for flag, enabled in required_flags.items():
            status = "✅ Enabled" if enabled else "❌ Disabled"
            print(f"   {status}: {flag}")
        
        if not all(required_flags.values()):
            print("\n❌ Required feature flags are not enabled. Cannot proceed with aggregation testing.")
            return False
        
        # Test 2: Data loading
        print("\n2. Testing data loading...")
        start_time = time.time()
        
        from utils.data_manager import get_global_data
        global_data = get_global_data()
        
        load_time = time.time() - start_time
        
        if global_data is not None and len(global_data) > 0:
            print(f"   ✅ Global data loaded: {len(global_data):,} records in {load_time:.3f}s")
        else:
            print(f"   ❌ Failed to load global data")
            return False
        
        # Test 3: Aggregator initialization
        print("\n3. Testing aggregator initialization...")
        start_time = time.time()
        
        from utils.data_aggregator import get_data_aggregator
        data_aggregator = get_data_aggregator()
        
        init_time = time.time() - start_time
        print(f"   ✅ Data aggregator initialized in {init_time:.3f}s")
        
        # Test 4: Pre-computation
        print("\n4. Testing aggregation pre-computation...")
        start_time = time.time()
        
        success = data_aggregator.precompute_aggregations(global_data)
        
        precompute_time = time.time() - start_time
        
        if success:
            print(f"   ✅ Aggregations pre-computed in {precompute_time:.3f}s")
        else:
            print(f"   ❌ Aggregation pre-computation failed")
            return False
        
        # Test 5: Aggregation availability
        print("\n5. Testing aggregation availability...")
        
        required_aggregations = ['state_subpart_totals', 'yearly_trends', 'subpart_summaries']
        available_aggregations = data_aggregator.get_available_aggregations()
        
        print(f"   Available aggregations: {available_aggregations}")
        
        all_available = True
        for agg_name in required_aggregations:
            if data_aggregator.is_aggregation_available(agg_name):
                data = data_aggregator.get_aggregation(agg_name)
                if data is not None and len(data) > 0:
                    print(f"   ✅ {agg_name}: Available ({len(data):,} records)")
                else:
                    print(f"   ⚠️ {agg_name}: Available but empty")
            else:
                print(f"   ❌ {agg_name}: Not available")
                all_available = False
        
        # Test 6: Aggregation status
        print("\n6. Testing aggregation status...")
        status = data_aggregator.get_aggregation_status()
        
        for category, success in status.items():
            status_text = "✅ Success" if success else "❌ Failed"
            print(f"   {status_text}: {category}")
        
        # Summary
        print("\n" + "=" * 70)
        print("Initialization Test Summary")
        print("=" * 70)
        
        if all_available and success:
            print("🎉 All tests passed! Data aggregator is properly initialized.")
            print(f"\nPerformance Summary:")
            print(f"   • Data loading: {load_time:.3f}s")
            print(f"   • Aggregator init: {init_time:.3f}s")
            print(f"   • Pre-computation: {precompute_time:.3f}s")
            print(f"   • Total time: {load_time + init_time + precompute_time:.3f}s")
            print(f"   • Available aggregations: {len(available_aggregations)}")
            return True
        else:
            print("⚠️ Some tests failed. Check the logs above for details.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the aggregation initialization test."""
    success = test_aggregation_initialization()
    
    if success:
        print("\n✅ Data aggregator is ready for performance testing.")
        print("\nNext steps:")
        print("1. Run the performance benchmark test")
        print("2. Test the complete application")
        print("3. Verify optimization effectiveness")
    else:
        print("\n❌ Data aggregator initialization failed.")
        print("\nTroubleshooting:")
        print("1. Check feature flag configuration")
        print("2. Verify data file availability")
        print("3. Check for import errors")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)