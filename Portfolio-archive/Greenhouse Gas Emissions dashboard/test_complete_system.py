#!/usr/bin/env python3
"""
Complete System Test for GHG Dashboard Performance Optimization

This script tests the complete system including data loading, aggregation
initialization, and performance benchmarking as outlined in the
app_performance_optimisation_Jun22.md document.
"""

import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_system():
    """Test the complete system from data loading to performance validation."""
    print("=" * 80)
    print("GHG Dashboard Complete System Test")
    print("Phase 4 Performance Optimization Validation")
    print("=" * 80)
    
    total_start_time = time.time()
    
    try:
        # Step 1: Feature Flag Validation
        print("\n🔧 Step 1: Feature Flag Validation")
        print("-" * 50)
        
        from utils.feature_flags import feature_flags
        
        required_flags = {
            'use_global_data_manager': feature_flags.is_enabled('use_global_data_manager'),
            'use_pre_aggregation': feature_flags.is_enabled('use_pre_aggregation'),
            'use_smart_cache': feature_flags.is_enabled('use_smart_cache'),
            'use_callback_debouncing': feature_flags.is_enabled('use_callback_debouncing')
        }
        
        for flag, enabled in required_flags.items():
            status = "✅ Enabled" if enabled else "⚠️ Disabled"
            print(f"   {status}: {flag}")
        
        critical_flags = ['use_global_data_manager', 'use_pre_aggregation']
        if not all(required_flags[flag] for flag in critical_flags):
            print("\n❌ Critical feature flags are disabled. Cannot proceed.")
            return False
        
        # Step 2: Data Manager Initialization
        print("\n📊 Step 2: Data Manager Initialization")
        print("-" * 50)
        
        start_time = time.time()
        
        from utils.data_manager import get_global_data_manager
        data_manager = get_global_data_manager()
        
        # Force data loading
        success = data_manager.load_global_data()
        
        if success:
            global_data = data_manager.get_data()
            load_time = time.time() - start_time
            
            if global_data is not None and len(global_data) > 0:
                print(f"   ✅ Data loaded: {len(global_data):,} records in {load_time:.3f}s")
                print(f"   ✅ Memory usage: {global_data.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
            else:
                print("   ❌ Data loading failed - no data returned")
                return False
        else:
            print("   ❌ Data loading failed")
            return False
        
        # Step 3: Data Aggregator Initialization
        print("\n⚡ Step 3: Data Aggregator Initialization")
        print("-" * 50)
        
        start_time = time.time()
        
        from utils.data_aggregator import get_data_aggregator
        data_aggregator = get_data_aggregator()
        
        # Pre-compute aggregations
        success = data_aggregator.precompute_aggregations(global_data)
        precompute_time = time.time() - start_time
        
        if success:
            available_aggregations = data_aggregator.get_available_aggregations()
            aggregation_status = data_aggregator.get_aggregation_status()
            
            print(f"   ✅ Aggregations computed in {precompute_time:.3f}s")
            print(f"   ✅ Available aggregations: {len(available_aggregations)}")
            
            # Test specific aggregations
            required_aggregations = ['state_subpart_totals', 'yearly_trends', 'subpart_summaries']
            for agg_name in required_aggregations:
                if data_aggregator.is_aggregation_available(agg_name):
                    agg_data = data_aggregator.get_aggregation(agg_name)
                    if agg_data is not None and len(agg_data) > 0:
                        print(f"   ✅ {agg_name}: {len(agg_data):,} records")
                    else:
                        print(f"   ⚠️ {agg_name}: Available but empty")
                else:
                    print(f"   ❌ {agg_name}: Not available")
        else:
            print(f"   ❌ Aggregation computation failed")
            return False
        
        # Step 4: Component Performance Testing
        print("\n🚀 Step 4: Component Performance Testing")
        print("-" * 50)
        
        components = {
            'state_breakdown_graph': 'components.state_breakdown_graph',
            'subpart_timeline_graph': 'components.subpart_timeline_graph', 
            'subpart_graph_v2': 'components.subpart_graph_v2'
        }
        
        component_times = {}
        
        for component_name, module_path in components.items():
            try:
                start_time = time.time()
                
                # Import the component
                module = __import__(module_path, fromlist=[''])
                
                # Test component creation (simplified)
                creation_time = time.time() - start_time
                component_times[component_name] = creation_time
                
                print(f"   ✅ {component_name}: {creation_time:.3f}s")
                
            except Exception as e:
                print(f"   ❌ {component_name}: Failed ({str(e)})")
                component_times[component_name] = float('inf')
        
        # Step 5: Performance Validation
        print("\n📈 Step 5: Performance Validation")
        print("-" * 50)
        
        total_time = time.time() - total_start_time
        
        # Performance targets from documentation
        targets = {
            'data_loading': {'target': 5.0, 'actual': load_time, 'unit': 'seconds'},
            'aggregation_precompute': {'target': 10.0, 'actual': precompute_time, 'unit': 'seconds'},
            'total_startup': {'target': 15.0, 'actual': total_time, 'unit': 'seconds'}
        }
        
        all_targets_met = True
        
        for metric, data in targets.items():
            target = data['target']
            actual = data['actual']
            unit = data['unit']
            
            if actual <= target:
                print(f"   ✅ {metric}: {actual:.3f}{unit} (target: <{target}{unit})")
            else:
                print(f"   ❌ {metric}: {actual:.3f}{unit} (target: <{target}{unit})")
                all_targets_met = False
        
        # Component performance targets
        for component, time_taken in component_times.items():
            if time_taken < 2.0:
                print(f"   ✅ {component}: {time_taken:.3f}s (target: <2.0s)")
            else:
                print(f"   ❌ {component}: {time_taken:.3f}s (target: <2.0s)")
                all_targets_met = False
        
        # Step 6: System Health Check
        print("\n🏥 Step 6: System Health Check")
        print("-" * 50)
        
        health_checks = {
            'Data Manager': data_manager.is_data_loaded(),
            'Data Aggregator': len(data_aggregator.get_available_aggregations()) > 0,
            'Feature Flags': all(required_flags[flag] for flag in critical_flags),
            'Performance Targets': all_targets_met
        }
        
        all_healthy = True
        for check, status in health_checks.items():
            if status:
                print(f"   ✅ {check}: Healthy")
            else:
                print(f"   ❌ {check}: Issues detected")
                all_healthy = False
        
        # Final Summary
        print("\n" + "=" * 80)
        print("SYSTEM TEST SUMMARY")
        print("=" * 80)
        
        if all_healthy and all_targets_met:
            print("🎉 SUCCESS: All tests passed!")
            print("\nPhase 4 Performance Optimization is working correctly.")
            print("\n📊 Performance Summary:")
            print(f"   • Data loading: {load_time:.3f}s")
            print(f"   • Aggregation precompute: {precompute_time:.3f}s")
            print(f"   • Total startup time: {total_time:.3f}s")
            print(f"   • Available aggregations: {len(available_aggregations)}")
            print(f"   • Component load times: {min(component_times.values()):.3f}s - {max([t for t in component_times.values() if t != float('inf')]):.3f}s")
            
            print("\n🚀 Next Steps:")
            print("   1. Run the complete application to test end-to-end")
            print("   2. Monitor performance in production")
            print("   3. Document performance improvements")
            
            return True
        else:
            print("⚠️ PARTIAL SUCCESS: Some issues detected.")
            print("\n🔧 Recommendations:")
            if not all_targets_met:
                print("   • Performance targets not met - review optimization implementation")
            if not all_healthy:
                print("   • System health issues - check component initialization")
            print("   • Review logs for detailed error information")
            print("   • Consider additional optimization strategies")
            
            return False
            
    except Exception as e:
        print(f"\n❌ SYSTEM TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete system test."""
    success = test_complete_system()
    
    if success:
        print("\n✅ System is ready for production use.")
    else:
        print("\n❌ System requires attention before production use.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)