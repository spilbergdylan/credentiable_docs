from typing import Dict

def is_contained_within(element: Dict, container: Dict, threshold: float = 0.8) -> bool:
    """
    Check if an element is spatially contained within a container.
    Returns True if the element is considered to be within the container's bounds.
    """
    # Get element bounds
    e_left = element.get('x', 0)
    e_top = element.get('y', 0)
    e_w = element.get('width', 0)
    e_h = element.get('height', 0)
    e_right = e_left + e_w
    e_bottom = e_top + e_h
    e_center_y = e_top + (e_h / 2)
    
    # Get container bounds
    c_left = container.get('x', 0)
    c_top = container.get('y', 0)
    c_w = container.get('width', 0)
    c_h = container.get('height', 0)
    c_right = c_left + c_w
    c_bottom = c_top + c_h
    c_center_y = c_top + (c_h / 2)
    
    # Special case for checkbox options within checkbox contexts
    if element.get('class') == 'checkbox_option' and container.get('class') == 'checkbox_context':
        # For checkbox options within checkbox_context, use a very low threshold (0.05 or 5% overlap)
        option_threshold = 0.05
        
        # Calculate overlap
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        # Check if option is vertically close to its context
        vertical_proximity = 150  # pixels - increased from 120
        is_vertically_close = (
            abs(e_top - c_bottom) < vertical_proximity or  # Option starts near context bottom
            abs(e_bottom - c_top) < vertical_proximity or  # Option ends near context top
            (e_top >= c_top and e_bottom <= c_bottom)     # Option is fully within context vertically
        )
        
        # Also check horizontal proximity
        horizontal_proximity = 100  # pixels
        is_horizontally_close = (
            abs(e_left - c_right) < horizontal_proximity or  # Option starts near context right
            abs(e_right - c_left) < horizontal_proximity or  # Option ends near context left
            (e_left >= c_left and e_right <= c_right)       # Option is fully within context horizontally
        )
        
        return (is_vertically_close or is_horizontally_close) and (overlap_area / element_area) > option_threshold
    
    # Special case for checkboxes within checkbox options
    if element.get('class') == 'checkbox' and container.get('class') == 'checkbox_option':
        # For checkboxes, we primarily care about y-coordinate proximity
        # since checkboxes are typically aligned with their options
        y_proximity = 20  # pixels - very small since checkboxes should be almost at the same y-level
        
        # Check if checkbox is at the same y-level as the option
        is_y_aligned = abs(e_center_y - c_center_y) < y_proximity
        
        # Also check if checkbox is to the left of the option text
        # (typically checkboxes appear before their labels)
        is_to_the_left = e_right < c_left + 30  # 30px buffer
        
        # For very small elements like checkboxes, we don't need much overlap
        # Just ensure they're close enough
        return is_y_aligned and is_to_the_left
    
    # Default case: Calculate overlap ratio
    overlap_width = min(e_right, c_right) - max(e_left, c_left)
    overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
    
    if overlap_width <= 0 or overlap_height <= 0:
        return False
        
    element_area = e_w * e_h
    overlap_area = overlap_width * overlap_height
    
    return (overlap_area / element_area) > threshold 