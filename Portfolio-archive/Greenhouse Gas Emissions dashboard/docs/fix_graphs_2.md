


          
# Implementation Plan for Graph Fixes

## Overview
We need to address two issues:
1. State GHG Emissions over Time graph not plotting correctly
2. Crowded labels in Emissions by Subpart pie chart for small percentages

## Approach
We'll follow a conservative, step-by-step approach to minimize risks and maintain existing functionality.

## Part 1: State GHG Emissions Graph Fix

### Investigation Steps
1. First, examine the state graph component code to identify where the error message is triggered
   - Look in <mcfile name="state_graph.py" path="components/state_graph.py"></mcfile>
   - Focus on the callback function that updates the graph
   - Check data processing logic and error handling

2. Debug the data flow
   - Verify the data structure being passed to the plotting function
   - Add logging statements to track:
     * Input data shape and content
     * Filter operations
     * Final data being passed to the plot

3. Examine axis configuration
   - Check how axes are being set/reset
   - Verify the conditions that trigger axis changes

### Implementation Plan
1. Create a new function `validate_state_data` in state_graph.py
   ```python
   def validate_state_data(df):
       """Validate the dataframe for state emissions plotting.
       
       Args:
           df (pd.DataFrame): Input dataframe
           
       Returns:
           tuple: (is_valid, error_message)
       """
   ```

2. Create a new function `prepare_state_plot_data` in state_graph.py
   ```python
   def prepare_state_plot_data(df, selected_states):
       """Prepare data for state emissions plot.
       
       Args:
           df (pd.DataFrame): Input dataframe
           selected_states (list): Selected state names
           
       Returns:
           pd.DataFrame: Processed dataframe ready for plotting
       """
   ```

3. Modify the existing callback to use these new functions
   - Add proper error handling
   - Maintain consistent axes labels
   - Return appropriate error messages when needed

## Part 2: Pie Chart Label Enhancement

### Implementation Plan
1. Create a new function `format_pie_labels` in subpart_graph.py
   ```python
   def format_pie_labels(values, labels, threshold=5.0):
       """Format pie chart labels based on percentage threshold.
       
       Args:
           values (array-like): Values for pie chart segments
           labels (array-like): Labels for segments
           threshold (float): Minimum percentage to show label (default: 5.0)
           
       Returns:
           tuple: (formatted_labels, hover_template)
       """
   ```

2. Modify the existing pie chart creation code to:
   - Calculate percentages
   - Apply the threshold logic
   - Update hover text to always show percentages
   - Hide labels for segments below threshold

## Testing Strategy
1. Test each new function independently
   - Create unit tests for `validate_state_data`
   - Create unit tests for `prepare_state_plot_data`
   - Create unit tests for `format_pie_labels`

2. Integration testing
   - Test state graph with various selections
   - Test pie chart with different data distributions
   - Verify hover functionality works correctly

## Rollback Plan
Create backup copies of modified files before making changes:
```bash
cp components/state_graph.py components/state_graph.py.backup
cp components/subpart_graph.py components/subpart_graph.py.backup
```

## Implementation Order
1. Start with pie chart labels (simpler change)
   - Implement and test `format_pie_labels`
   - Update pie chart creation code
   - Verify changes work as expected

2. Then address state graph issues
   - Implement validation and data preparation functions
   - Update callback with new functions
   - Test thoroughly

## Notes for Junior Developers
- Always add detailed comments explaining the logic
- Use meaningful variable names
- Add logging statements for debugging
- Test changes incrementally
- Keep the original code structure
- Follow existing code style and patterns
- Document any assumptions made
- Handle edge cases (empty data, null values, etc.)

This plan provides a structured approach to fix both issues while maintaining code quality and minimizing risks. Each step is designed to be testable and reversible if needed.
        