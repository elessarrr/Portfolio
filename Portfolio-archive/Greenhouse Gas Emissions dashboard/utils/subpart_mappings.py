from typing import List, Dict, Optional

# Subpart mappings for GHG emissions categories
subpart_mappings: Dict[str, str] = {
    'A': 'General Provisions',
    'B': '(Reserved)',
    'C': 'General Stationary Fuel Combustion Sources',
    'D': 'Electricity Generation',
    'E': 'Adipic Acid Production',
    'F': 'Aluminum Production',
    'G': 'Ammonia Manufacturing',
    'H': 'Cement Production',
    'I': 'Electronics Manufacturing',
    'J': 'Ethanol Production',
    'K': 'Ferroalloy Production',
    'L': 'Fluorinated Gas Production',
    'M': 'Food Processing',
    'N': 'Glass Production',
    'O': 'HCFC-22 Production and HFC-23 Destruction',
    'P': 'Hydrogen Production',
    'Q': 'Iron and Steel Production',
    'R': 'Lead Production',
    'S': 'Lime Manufacturing',
    'T': 'Magnesium Production',
    'U': 'Miscellaneous Uses of Carbonate',
    'V': 'Nitric Acid Production',
    'W': 'Petroleum and Natural Gas Systems',
    'X': 'Petrochemical Production',
    'Y': 'Petroleum Refineries',
    'Z': 'Phosphoric Acid Production',
    'AA': 'Pulp and Paper Manufacturing',
    'BB': 'Silicon Carbide Production',
    'CC': 'Soda Ash Manufacturing',
    'DD': 'Use of Electric Transmission and Distribution Equipment',
    'EE': 'Titanium Dioxide Production',
    'FF': 'Underground Coal Mines',
    'GG': 'Zinc Production',
    'HH': 'Municipal Solid Waste Landfills',
    'II': 'Industrial Wastewater Treatment',
    'JJ': 'Manure Management',
    'KK': 'Suppliers of Coal',
    'LL': 'Suppliers of Coal-based Liquid Fuels',
    'MM': 'Suppliers of Petroleum Products',
    'NN': 'Suppliers of Natural Gas and Natural Gas Liquids',
    'OO': 'Suppliers of Industrial Greenhouse Gases',
    'PP': 'Suppliers of Carbon Dioxide',
    'QQ': 'Imports and Exports of Equipment Pre-charged with Fluorinated GHGs',
    'RR': 'Geologic Sequestration of Carbon Dioxide',
    'SS': 'Manufacture of Electric Transmission and Distribution Equipment',
    'TT': 'Industrial Waste Landfills',
    'UU': 'Injection of Carbon Dioxide',
    'VV': 'Geologic Sequestration of Carbon Dioxide with Enhanced Oil Recovery',
    'WW': 'Coke Calciners',
    'XX': 'Calcium Carbide Producers',
    'YY': 'Caprolactam, Glyoxal, and Glyoxylic Acid Production',
    'ZZ': 'Ceramics Manufacturing'
}

def get_subpart_description(code: str) -> str:
    """Get description from subpart code."""
    return subpart_mappings.get(code, code)

def get_subpart_code(description: str) -> str:
    """Get subpart code from description."""
    for code, desc in subpart_mappings.items():
        if desc == description:
            return code
    return description

def get_all_subpart_descriptions() -> List[str]:
    """Get all subpart descriptions as a list.
    
    Returns:
        List[str]: List of all subpart descriptions
    """
    return list(subpart_mappings.values())

def validate_subpart_code(code: str) -> bool:
    """Validate if a subpart code exists in the mappings.
    
    Args:
        code: The subpart code to validate
        
    Returns:
        bool: True if the code is valid, False otherwise
    """
    return code in subpart_mappings

def get_valid_subpart_codes(codes: List[str]) -> List[str]:
    """Filter and return only valid subpart codes.
    
    Args:
        codes: List of subpart codes to validate
        
    Returns:
        List[str]: List of valid subpart codes
    """
    return [code for code in codes if validate_subpart_code(code)]