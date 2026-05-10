from typing import Dict, List


def default_jasc_seed() -> List[Dict[str, str]]:
    return [
        {'jasc_code': '21-00-00', 'system_name': 'Air Conditioning'},
        {'jasc_code': '24-00-00', 'system_name': 'Electrical Power'},
        {'jasc_code': '27-00-00', 'system_name': 'Flight Controls'},
        {'jasc_code': '28-00-00', 'system_name': 'Fuel'},
        {'jasc_code': '29-00-00', 'system_name': 'Hydraulics'},
        {'jasc_code': '32-00-00', 'system_name': 'Landing Gear'},
        {'jasc_code': '34-00-00', 'system_name': 'Navigation'},
        {'jasc_code': '36-00-00', 'system_name': 'Pneumatic'},
        {'jasc_code': '49-00-00', 'system_name': 'Auxiliary Power Unit'},
        {'jasc_code': '71-00-00', 'system_name': 'Powerplant'},
    ]

