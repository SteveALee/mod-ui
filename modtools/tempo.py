# List of all subdividers' 'value's and 'label's
dividers = [{
    'value': 0.333,
    'label': "2T"
  },
  {
    'value': 0.5,
    'label': "2"
  },
  {
    'value': 0.75,
    'label': "2."
  },{
    'value': 0.666,
    'label': "1T"
  },
  {
    'value': 1,
    'label': "1"
  },
  {
    'value': 1.5,
    'label': "1."
  },
  {
    'value': 1.333,
    'label': "1/2T"
  },
  {
    'value': 2,
    'label': "1/2"
  },
  {
    'value': 3,
    'label': "1/2."
  },
  {
    'value': 2.666,
    'label': "1/4T"
  },
  {
    'value': 4,
    'label': "1/4"
  },
  {
    'value': 6,
    'label': "1/4."
  },
  {
    'value': 5.333,
    'label': "1/8T"
  },
  {
    'value': 8,
    'label': "1/8"
  },
  {
    'value': 12,
    'label': "1/8."
  },
  {
    'value': 10.666,
    'label': "1/16T"
  },
  {
    'value': 16,
    'label': "1/16"
  },
  {
    'value': 24,
    'label': "1/16."
  },
  {
    'value': 21.333,
    'label': "1/32T"
  },
  {
    'value': 32,
    'label': "1/32"
  },
  {
    'value': 48,
    'label': "1/32."
  }
]

unit_conversion_factors = {
  # to/from s:
  's': {
    'to': 1,
    'from': 1
  },
  'ms': {
    'to': 0.001,
    'from': 1000
  },
  'min': {
    'to': 60.0,
    'from': 1 / 60.0,
  },
  # to/from Hz:
  'Hz': {
    'to': 1,
    'from': 1,
  },
  'MHz': {
    'to': 1000000,
    'from': 0.000001,
  },
  'kHz': {
    'to': 1000,
    'from': 0.001,
  }
}

def get_filtered_dividers(smin, smax):
    """Get list of filtered dividers s such as smin <= s <= smax

    Args:
        smin (float): min divider value
        smax (float): max divider value

    Returns:
        list: filtered dividers as dicts with subdivider value and label
    """
    filtered_dividers = []
    for d in dividers:
        if smin <= d['value'] and d['value'] <= smax:
            filtered_dividers.append(d)
    return filtered_dividers

def get_divider_value(b, v):
    """Compute divider value

    Args:
        b (float): BPM s-1
        v (float): control port value in seconds

    Returns:
        float: divider value
    """
    return 240 / (b * v)

def get_port_value(b, s):
    """Compute Control Port value if BPM addressed

    Args:
        b (float): BPM s-1
        s (float): divider value (subdivider)

    Returns:
        float: control port value in seconds
    """
    return 240 / (b * s)

def convert_equivalent(value, conversion_factor, port_unit_symbol):
    """Convert value in any of the listed units to equivalent in seconds or value in seconds to any of the listed units

    Args:
        value (float): input value
        conversion_factor (float): Conversion factor based on unit_conversion_factors
        port_unit_symbol (string): Control port unit symbol

    Returns:
        float: output value
    """
    if port_unit_symbol == "s" or port_unit_symbol == "ms" or port_unit_symbol == "min":
        return round(conversion_factor * value, 3)
    elif port_unit_symbol == "Hz" or port_unit_symbol == "MHz" or port_unit_symbol == "kHz":
        if value == 0: # avoid division by zero
            value = 0.001
        return round(conversion_factor / value, 3)
    else:
        return None

def convert_seconds_to_port_value_equivalent(value, port_unit_symbol):
    """Convert value in seconds to control port unit

    Args:
        value (float): Value in seconds
        port_unit_symbol (string): Control port unit symbol

    Returns:
        float: Equivalent value using control port unit
    """
    unit = unit_conversion_factors.get(port_unit_symbol, None)
    if unit is None:
        return None
    conversion_factor = unit['from']
    return convert_equivalent(value, conversion_factor, port_unit_symbol)

def convert_port_value_to_seconds_equivalent(value, port_unit_symbol):
    """Convert value from one of the listed units to seconds equivalent

    Args:
        value (float): Control port value (usually min or max)
        port_unit_symbol (string): Control port unit symbol

    Returns:
        float: Equivalent value in seconds
    """
    unit = unit_conversion_factors.get(port_unit_symbol, None)
    if unit is None:
        return None
    conversion_factor = unit['to']
    return convert_equivalent(value, conversion_factor, port_unit_symbol)

def get_options_port_values(port_unit_symbol, b, divider_options):
    """Get list of possible port values based on bpm and list of dividers

    Args:
        port_unit_symbol (string): Control port unit symbol
        b (float): bpm
        divider_options (list): list of dicts { value: dividerValue, label: dividerLabel }

    Returns:
        list: list of dicts { value: portValue, label: dividerLabel }
    """
    if divider_options is None:
        return None
    port_values_with_divider_labels = []
    for option in divider_options:
        port_value_sec = get_port_value(b, option['value'])
        port_value = convert_seconds_to_port_value_equivalent(port_value_sec, port_unit_symbol)
        port_values_with_divider_labels.append({'value': port_value, 'label': option['label']})
    return port_values_with_divider_labels

def get_value_from_options(options, divider_value):
    """Get value from options list where label corresponds to divider_value

    Args:
        options: list of dicts { value: portValue, label: dividerLabel }
        divider_value (float): subdivider value

    Returns:
        value (flat): corresponding port value
    """
    divider_label = None
    value = None
    for i, divider in enumerate(dividers):
        if divider['value'] == divider_value:
            divider_label = divider['label']
    if divider_label:
        for i, option in enumerate(options):
            if option['label'] == divider_label:
                value = option['value']
    return value


def get_divider_options(port, min_bpm, max_bpm):
    """Get dividers options for given port and bpmPort min and max

    Args:
        port (dict): port info
        min_bpm (float): minimum value for bpm
        max_bpm (float): maximum value for bpm

    Return:
     list: all available dividers as dicts with subdivider value and label
    """
    # First, convert min and max port values to equivalent in seconds
    min_value = convert_port_value_to_seconds_equivalent(port['ranges']['minimum'], port['units']['symbol'])
    max_value = convert_port_value_to_seconds_equivalent(port['ranges']['maximum'], port['units']['symbol'])

    # Then, compute min and max subdividers that will fit all bpms
    s1_min_bpm = get_divider_value(min_bpm, min_value)
    s2_min_bpm = get_divider_value(min_bpm, max_value)
    s1_max_bpm = get_divider_value(max_bpm, min_value)
    s2_max_bpm = get_divider_value(max_bpm, max_value)

    if "hasStrictBounds" in port['properties']:
        smin = max(s1_min_bpm, s1_max_bpm) if s1_min_bpm < s2_min_bpm else max(s2_min_bpm, s2_max_bpm)
        smax = min(s2_min_bpm, s2_max_bpm) if s1_min_bpm < s2_min_bpm else min(s1_min_bpm, s1_max_bpm)
    else:
        smin = min(s1_min_bpm, s2_min_bpm, s1_max_bpm, s2_max_bpm)
        smax = max(s1_min_bpm, s2_min_bpm, s1_max_bpm, s2_max_bpm)

    return get_filtered_dividers(smin, smax)
