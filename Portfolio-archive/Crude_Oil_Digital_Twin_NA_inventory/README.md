# Crude Oil Digital Twin Application

A digital twin application for monitoring, analyzing, and simulating crude oil inventory across different U.S. PADD (Petroleum Administration for Defense Districts) regions. This application provides real-time visualization, trend analysis, and scenario-based simulations for better decision-making in crude oil inventory management.

## Features

### Real-time Monitoring
- Inventory tracking across PADD regions (weekly data frequency update)
- Current WTI crude oil price integration (weekly data frequency update)

### Advanced Visualization
- Multi-region inventory trend analysis
- Interactive PADD region selector with map
- Risk gauge visualization for inventory levels

### Scenario Simulation
- Customizable simulation duration (4-52 weeks)
- Multiple scenario options:
  - Production Cut Scenario
  - Demand Spike Scenario
  - Strategic Reserve Release
- Daily consumption rate adjustment
- Risk assessment and impact analysis

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv venv_streamlit
source venv_streamlit/bin/activate  # On Windows: .\venv_streamlit\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run app_crude_odt_trae_13Mar_v2.py
```

2. Select PADD Region:
   - Use the sidebar to choose a specific PADD region
   - View the PADD region map for reference

3. Configure Simulation Parameters:
   - Adjust simulation duration
   - Set daily consumption rate
   - Toggle different scenario options

4. Analyze Results:
   - Monitor inventory trends
   - Review risk assessments
   - Evaluate scenario impacts

## Technical Architecture

### Module Structure

- **data_handler.py**: Data processing and management
- **simulation.py**: Scenario simulation engine
- **visualization.py**: Data visualization and UI components

### Key Components

1. **Data Handling**
   - Historical data processing
   - Real-time data integration
   - Data validation and error handling

2. **Simulation Engine**
   - Scenario-based modeling
   - Risk calculation
   - Impact assessment

3. **Visualization Layer**
   - Interactive plots using Plotly
   - Streamlit UI components
   - Real-time metric updates

## Error Handling

The application implements comprehensive error handling through decorators and try-except blocks to ensure robust operation and meaningful error messages.

## Dependencies

- streamlit
- plotly
- pandas
- numpy
- python-dotenv

## Best Practices employed

1. **Modular Architecture**: Separation of concerns between data, simulation, and visualization
2. **Error Handling**: Comprehensive exception handling through decorators
3. **Caching Strategy**: Efficient data loading with appropriate TTL settings
4. **Responsive Design**: Adapts to different screen sizes and data contexts

## Support

For issues and feature requests, please create an issue in the repository.

## License

This project is open source and available under the MIT License.

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED.
