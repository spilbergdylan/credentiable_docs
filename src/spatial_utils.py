from typing import Dict

def is_contained_within(element: Dict, container: Dict, threshold: float = 0.8) -> bool:
    """
    Check if one element is contained within another based on bounding boxes.
    
    Args:
        element: The element to check if it's contained within the container
        container: The container element
        threshold: The overlap threshold (default: 0.8 or 80%)
        
    Returns:
        bool: True if the element is contained within the container, False otherwise
    """
    e_x = float(element['x'])
    e_y = float(element['y'])
    e_w = float(element['width'])
    e_h = float(element['height'])
    
    c_x = float(container['x'])
    c_y = float(container['y'])
    c_w = float(container['width'])
    c_h = float(container['height'])
    
    e_left = e_x - (e_w / 2)
    e_right = e_x + (e_w / 2)
    e_top = e_y - (e_h / 2)
    e_bottom = e_y + (e_h / 2)
    
    c_left = c_x - (c_w / 2)
    c_right = c_x + (c_w / 2)
    c_top = c_y - (c_h / 2)
    c_bottom = c_y + (c_h / 2)
    
    # Special case for tables
    if element.get('class') == 'table':
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # For tables, require at least 30% vertical overlap with the section
        vertical_overlap_ratio = overlap_height / e_h
        if vertical_overlap_ratio < 0.3:  # Less than 30% vertical overlap
            return False
        
        # Also require significant horizontal overlap (at least 20%)
        horizontal_overlap_ratio = overlap_width / min(e_w, c_w)
        if horizontal_overlap_ratio < 0.2:  # Less than 20% horizontal overlap
            return False
        
        # Check if table is vertically positioned within or very close to the section
        vertical_proximity = 100  # pixels
        is_vertically_close = (
            (e_top >= c_top - vertical_proximity and e_bottom <= c_bottom + vertical_proximity) or  # Table is within or very close to section
            (e_top <= c_bottom + vertical_proximity and e_bottom >= c_top - vertical_proximity)     # Table overlaps with section
        )
        
        return is_vertically_close
    
    # Special case for fields within tables
    if element.get('class') in ['field', 'checkbox', 'checkbox_option', 'checkbox_context'] and container.get('class') == 'table':
        # Check if the element's center point is within the container's bounds
        return (c_left <= e_x <= c_right) and (c_top <= e_y <= c_bottom)
    
    # Special case for checkbox hierarchy
    if element.get('class') in ['checkbox', 'checkbox_option'] and container.get('class') == 'checkbox_context':
        # For checkboxes within checkbox_context, use a much lower threshold (0.05 or 5% overlap)
        checkbox_threshold = 0.05
        
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # Also check if checkbox is vertically close to its context
        vertical_proximity = 150  # pixels
        is_vertically_close = (
            abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near context bottom
            abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near context top
            (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within context vertically
        )
        
        return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
    
    # Special case for checkbox options within checkbox contexts
    if element.get('class') == 'checkbox_option' and container.get('class') == 'checkbox_context':
        # For checkbox options within checkbox_context, use a lower threshold (0.1 or 10% overlap)
        option_threshold = 0.1
        
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # Also check if option is vertically close to its context
        vertical_proximity = 150  # pixels
        is_vertically_close = (
            abs(e_top - c_bottom) < vertical_proximity or  # Option starts near context bottom
            abs(e_bottom - c_top) < vertical_proximity or  # Option ends near context top
            (e_top >= c_top and e_bottom <= c_bottom)     # Option is fully within context vertically
        )
        
        return is_vertically_close and (overlap_area / element_area) > option_threshold
    
    # Special case for checkboxes within checkbox options
    if element.get('class') == 'checkbox' and container.get('class') == 'checkbox_option':
        # For checkboxes within checkbox_option, use a very low threshold (0.02 or 2% overlap)
        checkbox_threshold = 0.02
        
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # Also check if checkbox is vertically close to its option
        vertical_proximity = 100  # pixels
        is_vertically_close = (
            abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near option bottom
            abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near option top
            (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within option vertically
        )
        
        return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
    
    # Special case for checkbox contexts within sections
    if element.get('class') == 'checkbox_context' and container.get('class') == 'section':
        # For checkbox contexts within sections, use a much lower threshold (0.1 or 10% overlap)
        context_threshold = 0.1
        
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # Also check if context is vertically close to its section
        vertical_proximity = 300  # pixels
        is_vertically_close = (
            abs(e_top - c_bottom) < vertical_proximity or  # Context starts near section bottom
            abs(e_bottom - c_top) < vertical_proximity or  # Context ends near section top
            (e_top >= c_top and e_bottom <= c_bottom)     # Context is fully within section vertically
        )
        
        return is_vertically_close and (overlap_area / element_area) > context_threshold
    
    # For other elements, use the original overlap calculation
    overlap_width = min(e_right, c_right) - max(e_left, c_left)
    overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
    
    if overlap_width <= 0 or overlap_height <= 0:
        return False
        
    element_area = e_w * e_h
    overlap_area = overlap_width * overlap_height
    
    return (overlap_area / element_area) > threshold 