import json
from typing import List, Dict, Any, Optional, Tuple

def build_document_hierarchy(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a hierarchical structure of a document based on bounding box information.
    
    The algorithm works by:
    1. Sorting elements by area (largest first)
    2. Determining parent-child relationships based on bounding box containment
    3. Building a tree structure representing the document hierarchy
    
    Args:
        elements: List of document elements with bounding box information
        
    Returns:
        A hierarchical representation of the document
    """
    # Calculate area and store original index for each element
    for i, element in enumerate(elements):
        # Calculate area and add it to the element
        element['area'] = element['width'] * element['height']
        element['original_index'] = i
        
        # Convert bounding box coordinates to actual box coordinates
        element['box'] = {
            'x1': element['x'] - element['width'] / 2,
            'y1': element['y'] - element['height'] / 2,
            'x2': element['x'] + element['width'] / 2,
            'y2': element['y'] + element['height'] / 2
        }
    
    # Sort elements by area in descending order
    elements.sort(key=lambda e: e['area'], reverse=True)
    
    # Create document tree
    document_tree = {'type': 'document', 'children': []}
    
    # Build parent-child relationships
    for i, element in enumerate(elements):
        # Find the smallest container that fully contains this element
        parent = find_parent(element, elements[:i], document_tree)
        
        # Skip text content for sections and tables as they often contain gibberish
        element_text = ''
        if element['class'].lower() not in ['section', 'table']:
            element_text = element.get('text', '')
        
        # Create node for this element with box as a space-separated string
        node = {
            'id': element['detection_id'],
            'type': element['class'],
            'text': element_text,
            'box': f"{element['x']} {element['y']} {element['width']} {element['height']}",
            'confidence': element['confidence']
        }
        
        # Add node to its parent's children
        if 'children' not in parent:
            parent['children'] = []
        parent['children'].append(node)
    
    # Sort children by y-coordinate (top to bottom) and then x-coordinate (left to right)
    sort_children_by_position(document_tree)
    
    # Remove empty children arrays
    clean_empty_children(document_tree)
    
    return document_tree

def find_parent(element: Dict[str, Any], potential_parents: List[Dict[str, Any]], 
                document_tree: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find the smallest container that fully contains the given element.
    
    Args:
        element: The element to find a parent for
        potential_parents: List of elements that could be parents
        document_tree: The root of the document tree
        
    Returns:
        The parent node
    """
    best_parent = document_tree
    best_area = float('inf')
    
    for parent in potential_parents:
        # Check if parent contains element
        if is_contained(element['box'], parent['box']):
            # Check if this is a better (smaller) parent than the current best
            if parent['area'] < best_area:
                # Find this parent in the existing tree
                parent_node = find_node_by_id(document_tree, parent['detection_id'])
                if parent_node:
                    best_parent = parent_node
                    best_area = parent['area']
    
    return best_parent

def is_contained(box1: Dict[str, float] | str, box2: Dict[str, float] | str, 
                 tolerance: float = 2.0) -> bool:
    """
    Check if box1 is contained within box2 with some tolerance.
    
    Args:
        box1: First bounding box either as dict with x1,y1,x2,y2 or as string "x y width height"
        box2: Second bounding box either as dict with x1,y1,x2,y2 or as string "x y width height"
        tolerance: Tolerance in pixels to allow for imprecise bounding boxes
        
    Returns:
        True if box1 is contained within box2, False otherwise
    """
    # Convert string format to coordinates if needed
    if isinstance(box1, str):
        parts = box1.split()
        x, y, width, height = map(float, parts)
        box1 = {
            'x1': x - width / 2,
            'y1': y - height / 2,
            'x2': x + width / 2,
            'y2': y + height / 2
        }
    
    if isinstance(box2, str):
        parts = box2.split()
        x, y, width, height = map(float, parts)
        box2 = {
            'x1': x - width / 2,
            'y1': y - height / 2,
            'x2': x + width / 2,
            'y2': y + height / 2
        }
        
    return (box1['x1'] >= box2['x1'] - tolerance and 
            box1['y1'] >= box2['y1'] - tolerance and 
            box1['x2'] <= box2['x2'] + tolerance and 
            box1['y2'] <= box2['y2'] + tolerance)

def find_node_by_id(tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a node in the tree by its ID.
    
    Args:
        tree: The tree to search
        node_id: The ID of the node to find
        
    Returns:
        The node if found, None otherwise
    """
    if tree.get('id') == node_id:
        return tree
    
    for child in tree.get('children', []):
        result = find_node_by_id(child, node_id)
        if result:
            return result
    
    return None

def sort_children_by_position(node: Dict[str, Any]) -> None:
    """
    Sort children of a node by y-coordinate (top to bottom) and then x-coordinate (left to right).
    
    Args:
        node: The node whose children to sort
    """
    if 'children' in node:
        # First sort by y-coordinate, then by x-coordinate
        # Extract coordinates from box string for sorting
        def get_coords(child):
            if isinstance(child['box'], str):
                parts = child['box'].split()
                return (float(parts[1]), float(parts[0]))  # y, x
            return (child['box']['y'], child['box']['x'])
            
        node['children'].sort(key=get_coords)
        
        # Recursively sort children of children
        for child in node['children']:
            sort_children_by_position(child)

def clean_empty_children(node: Dict[str, Any]) -> None:
    """
    Recursively remove empty 'children' arrays from the document hierarchy.
    
    Args:
        node: The node to clean
    """
    if 'children' in node:
        # Process all children first
        for child in node['children']:
            clean_empty_children(child)
        
        # If children array is empty, remove it
        if not node['children']:
            del node['children']

def process_document(json_data: str) -> Dict[str, Any]:
    """
    Process a document from JSON data.
    
    Args:
        json_data: JSON string containing document elements
        
    Returns:
        A hierarchical representation of the document
    """
    elements = json.loads(json_data)
    hierarchy = build_document_hierarchy(elements)
    return hierarchy

def print_hierarchy(node: Dict[str, Any], level: int = 0) -> None:
    """
    Print the hierarchy in a human-readable format.
    
    Args:
        node: The node to print
        level: The indentation level
    """
    indent = "  " * level
    
    if 'type' in node:
        if node['type'] == 'document':
            print(f"{indent}Document")
        else:
            text_preview = node.get('text', '')
            if text_preview:
                text_preview = text_preview[:50]
            print(f"{indent}{node['type']}: {text_preview}")
    
    for child in node.get('children', []):
        print_hierarchy(child, level + 1)

# Example usage:
# with open("document_data.json", "r") as f:
#     json_data = f.read()
# 
# hierarchy = process_document(json_data)
# print_hierarchy(hierarchy)
#
# # To get JSON output:
# print(json.dumps(hierarchy, indent=2))