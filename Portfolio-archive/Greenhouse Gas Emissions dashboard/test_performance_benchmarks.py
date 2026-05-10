#!/usr/bin/env python3
"""
Performance Benchmark Tests for GHG Dashboard Optimization

This script measures and validates performance improvements after Phase 4 completion.
Tests startup times, graph loading times, and optimization effectiveness.
"""

import os
import sys
import time
import gc
from typing import Dict, List, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class PerformanceBenchmark:
    """Performance benchmarking suite for the GHG dashboard."""
    
    def __init__(self):
        """Initialize the performance benchmark suite."""
        self.results = {}
    
    def measure_startup_time(self) -> float:
        """Measure application startup time."""
        print("\n=== Testing Application Startup Time ===")
        
        start_time = time.time()
        
        try:
            # Import and initialize the app
            from utils.data_manager import get_global_data
            from utils.data_aggregator import get_data_aggregator
            from utils.feature_flags import feature_flags
            
            # Measure data manager initialization
            data_start = time.time()
            data = get_global_data()
            data_time = time.time() - data_start
            
            # Measure aggregator initialization if enabled
            agg_time = 0
            if feature_flags.is_enabled('use_pre_aggregation'):
                agg_start = time.time()
                aggregator = get_data_aggregator()
                agg_time = time.time() - agg_start
            
            total_time = time.time() - start_time
            
            print(f"✅ Data manager initialization: {data_time:.3f}s")
            print(f"✅ Data aggregator initialization: {agg_time:.3f}s")
            print(f"✅ Total startup time: {total_time:.3f}s")
            
            return total_time
            
        except Exception as e:
            print(f"❌ Startup test failed: {str(e)}")
            return float('inf')
    
    def measure_component_loading_time(self, component_name: str) -> Dict[str, float]:
        """Measure component loading time with and without optimization."""
        print(f"\n=== Testing {component_name} Loading Time ===")
        
        results = {}
        
        try:
            if component_name == 'state_breakdown_graph':
                from components.state_breakdown_graph import create_state_breakdown_graph
                
                # Mock app for testing
                class MockApp:
                    def callback(self, *args, **kwargs):
                        def decorator(func):
                            return func
                        return decorator
                
                mock_app = MockApp()
                
                # Test component creation time
                start_time = time.time()
                component = create_state_breakdown_graph(mock_app)
                creation_time = time.time() - start_time
                
                results['creation_time'] = creation_time
                print(f"✅ {component_name} creation time: {creation_time:.3f}s")
                
            elif component_name == 'subpart_timeline_graph':
                from components.subpart_timeline_graph import create_subpart_timeline_graph
                
                class MockApp:
                    def callback(self, *args, **kwargs):
                        def decorator(func):
                            return func
                        return decorator
                
                mock_app = MockApp()
                
                start_time = time.time()
                component = create_subpart_timeline_graph(mock_app)
                creation_time = time.time() - start_time
                
                results['creation_time'] = creation_time
                print(f"✅ {component_name} creation time: {creation_time:.3f}s")
                
            elif component_name == 'subpart_graph_v2':
                from components.subpart_graph_v2 import create_enhanced_subpart_graph
                
                class MockApp:
                    def callback(self, *args, **kwargs):
                        def decorator(func):
                            return func
                        return decorator
                
                mock_app = MockApp()
                
                start_time = time.time()
                component = create_enhanced_subpart_graph(mock_app)
                creation_time = time.time() - start_time
                
                results['creation_time'] = creation_time
                print(f"✅ {component_name} creation time: {creation_time:.3f}s")
                
        except Exception as e:
            print(f"❌ {component_name} loading test failed: {str(e)}")
            results['creation_time'] = float('inf')
        
        return results
    
    def measure_data_access_performance(self) -> Dict[str, float]:
        """Measure data access performance with optimizations."""
        print("\n=== Testing Data Access Performance ===")
        
        results = {}
        
        try:
            from utils.data_manager import get_global_data
            from utils.data_aggregator import get_data_aggregator
            from utils.feature_flags import feature_flags
            
            # Test global data access
            start_time = time.time()
            data = get_global_data()
            global_data_time = time.time() - start_time
            results['global_data_access'] = global_data_time
            print(f"✅ Global data access: {global_data_time:.3f}s")
            
            # Test pre-aggregated data access if enabled
            if feature_flags.is_enabled('use_pre_aggregation'):
                aggregator = get_data_aggregator()
                
                # Test state_subpart_totals access
                start_time = time.time()
                state_data = aggregator.get_aggregation('state_subpart_totals')
                state_time = time.time() - start_time
                results['state_subpart_totals'] = state_time
                print(f"✅ State subpart totals access: {state_time:.3f}s")
                
                # Test yearly_trends access
                start_time = time.time()
                trends_data = aggregator.get_aggregation('yearly_trends')
                trends_time = time.time() - start_time
                results['yearly_trends'] = trends_time
                print(f"✅ Yearly trends access: {trends_time:.3f}s")
                
                # Test subpart_summaries access
                start_time = time.time()
                summaries_data = aggregator.get_aggregation('subpart_summaries')
                summaries_time = time.time() - start_time
                results['subpart_summaries'] = summaries_time
                print(f"✅ Subpart summaries access: {summaries_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Data access test failed: {str(e)}")
        
        return results
    
    def test_optimization_effectiveness(self) -> Dict[str, bool]:
        """Test that optimizations are properly configured and working."""
        print("\n=== Testing Optimization Effectiveness ===")
        
        results = {}
        
        try:
            from utils.feature_flags import feature_flags
            from utils.data_aggregator import get_data_aggregator
            
            # Test feature flags
            optimization_flags = {
                'use_global_data_manager': feature_flags.is_enabled('use_global_data_manager'),
                'use_smart_cache': feature_flags.is_enabled('use_smart_cache'),
                'use_callback_debouncing': feature_flags.is_enabled('use_callback_debouncing'),
                'use_pre_aggregation': feature_flags.is_enabled('use_pre_aggregation')
            }
            
            for flag, enabled in optimization_flags.items():
                results[flag] = enabled
                status = "✅ Enabled" if enabled else "❌ Disabled"
                print(f"{status}: {flag}")
            
            # Test pre-aggregated data availability
            if optimization_flags['use_pre_aggregation']:
                aggregator = get_data_aggregator()
                required_aggregations = ['state_subpart_totals', 'yearly_trends', 'subpart_summaries']
                
                for agg_name in required_aggregations:
                    try:
                        data = aggregator.get_aggregation(agg_name)
                        available = data is not None and len(data) > 0
                        results[f'{agg_name}_available'] = available
                        status = "✅ Available" if available else "❌ Not available"
                        print(f"{status}: {agg_name} aggregation")
                    except Exception as e:
                        results[f'{agg_name}_available'] = False
                        print(f"❌ Error accessing {agg_name}: {str(e)}")
            
        except Exception as e:
            print(f"❌ Optimization effectiveness test failed: {str(e)}")
        
        return results
    
    def run_comprehensive_benchmark(self) -> Dict[str, any]:
        """Run the complete performance benchmark suite."""
        print("=" * 70)
        print("GHG Dashboard Performance Benchmark Suite")
        print("=" * 70)
        
        all_results = {}
        
        # Test 1: Startup Performance
        startup_time = self.measure_startup_time()
        all_results['startup_time'] = startup_time
        
        # Test 2: Component Loading Performance
        components = ['state_breakdown_graph', 'subpart_timeline_graph', 'subpart_graph_v2']
        component_results = {}
        
        for component in components:
            component_results[component] = self.measure_component_loading_time(component)
        
        all_results['component_loading'] = component_results
        
        # Test 3: Data Access Performance
        data_access_results = self.measure_data_access_performance()
        all_results['data_access'] = data_access_results
        
        # Test 4: Optimization Effectiveness
        optimization_results = self.test_optimization_effectiveness()
        all_results['optimization_effectiveness'] = optimization_results
        
        return all_results
    
    def validate_performance_targets(self, results: Dict[str, any]) -> bool:
        """Validate that performance targets are met."""
        print("\n" + "=" * 70)
        print("Performance Target Validation")
        print("=" * 70)
        
        targets_met = True
        
        # Target: Graph loading time < 2 seconds
        component_times = results.get('component_loading', {})
        for component, times in component_times.items():
            creation_time = times.get('creation_time', float('inf'))
            if creation_time < 2.0:
                print(f"✅ {component} creation time: {creation_time:.3f}s (< 2.0s target)")
            else:
                print(f"❌ {component} creation time: {creation_time:.3f}s (≥ 2.0s target)")
                targets_met = False
        
        # Target: Data access time should be minimal
        data_access = results.get('data_access', {})
        for access_type, access_time in data_access.items():
            if access_time < 0.1:
                print(f"✅ {access_type} access time: {access_time:.3f}s (< 0.1s)")
            else:
                print(f"⚠️ {access_type} access time: {access_time:.3f}s (≥ 0.1s)")
        
        # Target: Optimization effectiveness
        optimization = results.get('optimization_effectiveness', {})
        critical_optimizations = ['use_pre_aggregation', 'use_global_data_manager']
        
        for opt in critical_optimizations:
            if optimization.get(opt, False):
                print(f"✅ {opt}: Enabled")
            else:
                print(f"❌ {opt}: Disabled")
                targets_met = False
        
        # Check aggregation availability
        aggregations = ['state_subpart_totals_available', 'yearly_trends_available', 'subpart_summaries_available']
        for agg in aggregations:
            if optimization.get(agg, False):
                print(f"✅ {agg.replace('_available', '')}: Available")
            else:
                print(f"⚠️ {agg.replace('_available', '')}: Not available")
        
        return targets_met
    
    def generate_performance_report(self, results: Dict[str, any]) -> str:
        """Generate a comprehensive performance report."""
        report = []
        report.append("\n" + "=" * 70)
        report.append("GHG Dashboard Performance Benchmark Report")
        report.append("=" * 70)
        
        # Startup Performance
        startup_time = results.get('startup_time', 0)
        report.append(f"\n📊 Startup Performance:")
        report.append(f"   • Total startup time: {startup_time:.3f}s")
        
        # Component Performance
        component_loading = results.get('component_loading', {})
        report.append(f"\n📊 Component Loading Performance:")
        for component, times in component_loading.items():
            creation_time = times.get('creation_time', 0)
            report.append(f"   • {component}: {creation_time:.3f}s")
        
        # Data Access Performance
        data_access = results.get('data_access', {})
        report.append(f"\n📊 Data Access Performance:")
        for access_type, access_time in data_access.items():
            report.append(f"   • {access_type}: {access_time:.3f}s")
        
        # Optimization Effectiveness
        optimization = results.get('optimization_effectiveness', {})
        report.append(f"\n📊 Optimization Status:")
        
        optimization_flags = ['use_global_data_manager', 'use_smart_cache', 'use_callback_debouncing', 'use_pre_aggregation']
        for flag in optimization_flags:
            status = "Enabled" if optimization.get(flag, False) else "Disabled"
            report.append(f"   • {flag}: {status}")
        
        aggregations = ['state_subpart_totals_available', 'yearly_trends_available', 'subpart_summaries_available']
        report.append(f"\n📊 Pre-computed Aggregations:")
        for agg in aggregations:
            status = "Available" if optimization.get(agg, False) else "Not available"
            agg_name = agg.replace('_available', '')
            report.append(f"   • {agg_name}: {status}")
        
        # Feature Flags Status
        try:
            from utils.feature_flags import feature_flags
            report.append(f"\n📊 Feature Flags Status:")
            flags = ['use_global_data_manager', 'use_smart_cache', 'use_callback_debouncing', 'use_pre_aggregation']
            for flag in flags:
                status = feature_flags.is_enabled(flag)
                report.append(f"   • {flag}: {'Enabled' if status else 'Disabled'}")
        except:
            report.append(f"\n⚠️ Could not retrieve feature flags status")
        
        return "\n".join(report)

def main():
    """Run the performance benchmark suite."""
    benchmark = PerformanceBenchmark()
    
    try:
        # Run comprehensive benchmarks
        results = benchmark.run_comprehensive_benchmark()
        
        # Validate performance targets
        targets_met = benchmark.validate_performance_targets(results)
        
        # Generate and display report
        report = benchmark.generate_performance_report(results)
        print(report)
        
        # Summary
        print("\n" + "=" * 70)
        print("Benchmark Summary")
        print("=" * 70)
        
        if targets_met:
            print("🎉 All performance targets met!")
            print("\nPhase 4 optimization is successful.")
            print("\nNext steps:")
            print("1. Run load testing with multiple users")
            print("2. Monitor performance in production")
            print("3. Document performance improvements")
        else:
            print("⚠️ Some performance targets not met.")
            print("\nRecommendations:")
            print("1. Review optimization implementation")
            print("2. Check feature flag configuration")
            print("3. Investigate performance bottlenecks")
        
        return targets_met
        
    except Exception as e:
        print(f"❌ Benchmark failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)