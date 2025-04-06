import json
from openai import OpenAI
import argparse
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

class DocumentStructurer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it in your .env file.")
        self.client = OpenAI(api_key=api_key)

    def _is_contained_within(self, element: Dict, container: Dict, threshold: float = 0.8) -> bool:
        """Check if one element is contained within another based on bounding boxes."""
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
            # For fields in tables, use a lower threshold (0.5 or 50% overlap)
            field_threshold = 0.5
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            return (overlap_area / element_area) > field_threshold
        
        # Special case for checkbox hierarchy
        if element.get('class') in ['checkbox', 'checkbox_option'] and container.get('class') == 'checkbox_context':
            # For checkboxes within checkbox_context, use a much lower threshold (0.1 or 10% overlap)
            checkbox_threshold = 0.1
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if checkbox is vertically close to its context
            vertical_proximity = 100  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near context bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near context top
                (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within context vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
        
        # Special case for checkbox options within checkbox contexts
        if element.get('class') == 'checkbox_option' and container.get('class') == 'checkbox_context':
            # For checkbox options within checkbox_context, use a lower threshold (0.2 or 20% overlap)
            option_threshold = 0.2
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if option is vertically close to its context
            vertical_proximity = 120  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Option starts near context bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Option ends near context top
                (e_top >= c_top and e_bottom <= c_bottom)     # Option is fully within context vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > option_threshold
        
        # Special case for checkboxes within checkbox options
        if element.get('class') == 'checkbox' and container.get('class') == 'checkbox_option':
            # For checkboxes within checkbox_option, use a very low threshold (0.05 or 5% overlap)
            checkbox_threshold = 0.05
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if checkbox is vertically close to its option
            vertical_proximity = 80  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near option bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near option top
                (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within option vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
        
        # Special case for checkbox contexts within sections
        if element.get('class') == 'checkbox_context' and container.get('class') == 'section':
            # For checkbox contexts within sections, use a lower threshold (0.3 or 30% overlap)
            context_threshold = 0.3
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if context is vertically close to its section
            vertical_proximity = 150  # pixels
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

    def _build_hierarchy(self, predictions: List[Dict]) -> Dict:
        """Build hierarchical structure from predictions."""
        # First, sort all elements by y-coordinate
        sorted_elements = sorted(predictions, key=lambda x: x['y'])
        
        # Create a map of all elements for quick lookup
        elements_map = {elem['detection_id']: elem for elem in predictions}
        
        # Track which elements have been assigned to tables
        assigned_to_tables = set()
        
        # First pass: Process tables and their contained elements
        tables = {}
        for elem in sorted_elements:
            if elem['class'] == 'table':
                table_id = elem['detection_id']
                table_elem = elements_map[table_id]
                
                # Find fields and checkbox contexts contained within this table
                table_fields = []
                table_checkbox_contexts = []
                
                for other_elem in sorted_elements:
                    if other_elem['detection_id'] == table_id:
                        continue
                        
                    if self._is_contained_within(other_elem, table_elem):
                        if other_elem['class'] == 'field':
                            table_fields.append(other_elem)
                            assigned_to_tables.add(other_elem['detection_id'])
                        elif other_elem['class'] == 'checkbox_context':
                            table_checkbox_contexts.append(other_elem)
                            assigned_to_tables.add(other_elem['detection_id'])
                
                # Create table entry with its fields and checkbox contexts
                tables[table_id] = {
                    'type': 'table',
                    'text': table_elem.get('text', ''),
                    'confidence': table_elem.get('confidence', 0.0),
                    'detection_id': table_id,
                    'fields': [{
                        'type': 'field',
                        'text': field.get('text', ''),
                        'confidence': field.get('confidence', 0.0),
                        'detection_id': field['detection_id']
                    } for field in table_fields],
                    'checkbox_contexts': []
                }
                
                # Process checkbox contexts within tables
                for context in table_checkbox_contexts:
                    context_id = context['detection_id']
                    context_options = []
                    
                    # Find checkbox options within this context
                    for option_elem in sorted_elements:
                        if option_elem['class'] == 'checkbox_option' and self._is_contained_within(option_elem, context):
                            option_id = option_elem['detection_id']
                            option_checkboxes = []
                            
                            # Find checkboxes within this option
                            for checkbox_elem in sorted_elements:
                                if checkbox_elem['class'] == 'checkbox' and self._is_contained_within(checkbox_elem, option_elem):
                                    option_checkboxes.append({
                                        'type': 'checkbox',
                                        'text': checkbox_elem.get('text', ''),
                                        'confidence': checkbox_elem.get('confidence', 0.0),
                                        'detection_id': checkbox_elem['detection_id']
                                    })
                            
                            context_options.append({
                                'type': 'checkbox_option',
                                'text': option_elem.get('text', ''),
                                'confidence': option_elem.get('confidence', 0.0),
                                'detection_id': option_id,
                                'checkboxes': option_checkboxes
                            })
                    
                    tables[table_id]['checkbox_contexts'].append({
                        'type': 'checkbox_context',
                        'text': context.get('text', ''),
                        'confidence': context.get('confidence', 0.0),
                        'detection_id': context_id,
                        'options': context_options
                    })
        
        # Second pass: Process sections and their contained elements
        sections = {}
        for elem in sorted_elements:
            if elem['class'] == 'section':
                section_id = elem['detection_id']
                section_elem = elements_map[section_id]
                
                # Find fields and checkbox contexts contained within this section
                # but not already assigned to tables
                section_fields = []
                section_checkbox_contexts = []
                
                for other_elem in sorted_elements:
                    if other_elem['detection_id'] == section_id:
                        continue
                        
                    if self._is_contained_within(other_elem, section_elem):
                        if other_elem['class'] == 'field' and other_elem['detection_id'] not in assigned_to_tables:
                            section_fields.append(other_elem)
                        elif other_elem['class'] == 'checkbox_context' and other_elem['detection_id'] not in assigned_to_tables:
                            section_checkbox_contexts.append(other_elem)
                
                # Process checkbox contexts within sections
                processed_checkbox_contexts = []
                for context in section_checkbox_contexts:
                    context_id = context['detection_id']
                    context_options = []
                    
                    # Find checkbox options within this context
                    for option_elem in sorted_elements:
                        if option_elem['class'] == 'checkbox_option' and self._is_contained_within(option_elem, context):
                            option_id = option_elem['detection_id']
                            option_checkboxes = []
                            
                            # Find checkboxes within this option
                            for checkbox_elem in sorted_elements:
                                if checkbox_elem['class'] == 'checkbox' and self._is_contained_within(checkbox_elem, option_elem):
                                    option_checkboxes.append({
                                        'type': 'checkbox',
                                        'text': checkbox_elem.get('text', ''),
                                        'confidence': checkbox_elem.get('confidence', 0.0),
                                        'detection_id': checkbox_elem['detection_id']
                                    })
                            
                            context_options.append({
                                'type': 'checkbox_option',
                                'text': option_elem.get('text', ''),
                                'confidence': option_elem.get('confidence', 0.0),
                                'detection_id': option_id,
                                'checkboxes': option_checkboxes
                            })
                    
                    processed_checkbox_contexts.append({
                        'type': 'checkbox_context',
                        'text': context.get('text', ''),
                        'confidence': context.get('confidence', 0.0),
                        'detection_id': context_id,
                        'options': context_options
                    })
                
                # Create section entry with its fields, tables, and checkbox contexts
                sections[section_id] = {
                    'width': section_elem.get('width', 0.0),
                    'height': section_elem.get('height', 0.0),
                    'x': section_elem.get('x', 0.0),
                    'y': section_elem.get('y', 0.0),
                    'confidence': section_elem.get('confidence', 0.0),
                    'class_id': section_elem.get('class_id', 0),
                    'class': section_elem.get('class', ''),
                    'detection_id': section_id,
                    'parent_id': section_elem.get('parent_id', ''),
                    'filename': section_elem.get('filename', ''),
                    'text': section_elem.get('text', ''),
                    'fields': [{
                        'width': field.get('width', 0.0),
                        'height': field.get('height', 0.0),
                        'x': field.get('x', 0.0),
                        'y': field.get('y', 0.0),
                        'confidence': field.get('confidence', 0.0),
                        'class_id': field.get('class_id', 0),
                        'class': field.get('class', ''),
                        'detection_id': field['detection_id'],
                        'parent_id': field.get('parent_id', ''),
                        'filename': field.get('filename', ''),
                        'text': field.get('text', '')
                    } for field in section_fields],
                    'tables': {table_id: table_data for table_id, table_data in tables.items() 
                             if self._is_contained_within(elements_map[table_id], section_elem)},
                    'checkbox_contexts': processed_checkbox_contexts
                }
        
        return sections

    def _enhance_structure_with_llm(self, structure: Dict, original_predictions: List[Dict]) -> Dict:
        """Enhance the document structure with LLM analysis."""
        # Create a map of all predictions for quick lookup
        predictions_map = {pred['detection_id']: pred for pred in original_predictions}
        
        # Prepare the prompt for the LLM
        prompt = """Analyze this document structure and:
1. Organize the fields into their respective sections
2. Clean up the text in fields, tables, and checkbox elements:
   - Fix OCR errors and typos
   - Remove extra spaces and newlines
   - Standardize formatting
   - Preserve important punctuation
   - Keep empty fields as empty strings
   - Maintain checkbox hierarchies (context -> option -> checkbox)

For each section, include ALL field IDs in the array for their respective sections.
Include ALL table IDs in the array for their respective sections.
Include ALL checkbox_context IDs in the array for their respective sections.

IMPORTANT: 
1. Use the section IDs exactly as they appear in the input structure. Do not add any prefixes or modify the IDs.
2. For tables, include ALL field IDs that belong to that table in the same array as the table ID.
3. Fields that belong to a table should be included in the same array as their parent table.
4. For checkbox contexts, include ALL checkbox_option IDs that belong to that context.
5. For checkbox options, include ALL checkbox IDs that belong to that option.
6. Return both the cleaned text and the original text for each field, table, and checkbox element.

The output should be a JSON object with two parts:
1. "structure": Object where keys are section IDs and values are arrays of field IDs, table IDs, and checkbox_context IDs
2. "cleaned_text": Object mapping detection_ids to their cleaned text values

Example format:
{
    "structure": {
        "d0adf60d-e72b-4ac3-b3a6-770ba7fdaf79": ["field_id_1", "field_id_2", "table_id_1", "checkbox_context_id_1"],
        "96088e19-833e-4ef6-95c6-7f4c653f7c38": ["field_id_5", "field_id_6", "table_id_2", "checkbox_context_id_2"]
    },
    "cleaned_text": {
        "field_id_1": "Last Name",
        "field_id_2": "First Name",
        "table_id_1": "Medical Licensure/Certification",
        "checkbox_context_id_1": "Gender",
        "checkbox_option_id_1": "Male",
        "checkbox_id_1": "☐"
    }
}

Current document structure:
"""
        
        # Add the current structure to the prompt
        prompt += json.dumps(structure, indent=2)
        
        # Get LLM response
        print("\n🔍 Raw LLM Output:")
        llm_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a document structure analyzer that returns only valid JSON with detection_ids. Always preserve checkbox hierarchies. Use section IDs exactly as they appear in the input. For tables, include all field IDs that belong to that table in the same array. Clean up text by fixing OCR errors and standardizing formatting."},
                {"role": "user", "content": prompt}
            ]
        ).choices[0].message.content
        print(llm_response)
        
        try:
            # Parse the LLM response
            llm_output = json.loads(llm_response)
            llm_structure = llm_output['structure']
            cleaned_text = llm_output.get('cleaned_text', {})
            
            # Create enhanced structure
            enhanced_structure = {}
            
            # Process each section
            for section_id, element_ids in llm_structure.items():
                if section_id not in structure:
                    continue
                    
                section_data = structure[section_id]
                
                # Track which fields have been assigned to tables
                fields_in_tables = set()
                
                # First, process tables and their fields
                tables = {}
                for element_id in element_ids:
                    if element_id in predictions_map:
                        element = predictions_map[element_id]
                        if element['class'] == 'table':
                            # Add table with all its metadata and cleaned text
                            tables[element_id] = {
                                'type': 'table',
                                'text': cleaned_text.get(element_id, element.get('text', '')),
                                'confidence': element.get('confidence', 0.0),
                                'detection_id': element_id,
                                'fields': [],
                                'checkbox_contexts': []
                            }
                            
                            # Find fields and checkbox contexts contained within this table
                            for field_id in element_ids:
                                if field_id in predictions_map:
                                    field = predictions_map[field_id]
                                    if field['class'] == 'field' and self._is_contained_within(field, element):
                                        tables[element_id]['fields'].append({
                                            'type': 'field',
                                            'text': cleaned_text.get(field_id, field.get('text', '')),
                                            'confidence': field.get('confidence', 0.0),
                                            'detection_id': field['detection_id']
                                        })
                                        fields_in_tables.add(field_id)
                                    elif field['class'] == 'checkbox_context' and self._is_contained_within(field, element):
                                        # Process checkbox context within table
                                        context_options = []
                                        for option_id in element_ids:
                                            if option_id in predictions_map:
                                                option = predictions_map[option_id]
                                                if option['class'] == 'checkbox_option' and self._is_contained_within(option, field):
                                                    option_checkboxes = []
                                                    for checkbox_id in element_ids:
                                                        if checkbox_id in predictions_map:
                                                            checkbox = predictions_map[checkbox_id]
                                                            if checkbox['class'] == 'checkbox' and self._is_contained_within(checkbox, option):
                                                                option_checkboxes.append({
                                                                    'type': 'checkbox',
                                                                    'text': cleaned_text.get(checkbox_id, checkbox.get('text', '')),
                                                                    'confidence': checkbox.get('confidence', 0.0),
                                                                    'detection_id': checkbox_id
                                                                })
                                                    context_options.append({
                                                        'type': 'checkbox_option',
                                                        'text': cleaned_text.get(option_id, option.get('text', '')),
                                                        'confidence': option.get('confidence', 0.0),
                                                        'detection_id': option_id,
                                                        'checkboxes': option_checkboxes
                                                    })
                                        tables[element_id]['checkbox_contexts'].append({
                                            'type': 'checkbox_context',
                                            'text': cleaned_text.get(field_id, field.get('text', '')),
                                            'confidence': field.get('confidence', 0.0),
                                            'detection_id': field_id,
                                            'options': context_options
                                        })
                
                # Now process remaining fields and checkbox contexts
                fields = []
                checkbox_contexts = []
                
                # First, add fields that are explicitly assigned to this section by the LLM
                for element_id in element_ids:
                    if element_id in predictions_map:
                        element = predictions_map[element_id]
                        if element['class'] == 'field' and element_id not in fields_in_tables:
                            # Add field with all its metadata and cleaned text
                            fields.append({
                                'width': element.get('width', 0.0),
                                'height': element.get('height', 0.0),
                                'x': element.get('x', 0.0),
                                'y': element.get('y', 0.0),
                                'confidence': element.get('confidence', 0.0),
                                'class_id': element.get('class_id', 0),
                                'class': element.get('class', ''),
                                'detection_id': element_id,
                                'parent_id': element.get('parent_id', ''),
                                'filename': element.get('filename', ''),
                                'text': cleaned_text.get(element_id, element.get('text', ''))
                            })
                        elif element['class'] == 'checkbox_context':
                            # Process checkbox context with its options and checkboxes
                            context_options = []
                            for option_id in element_ids:
                                if option_id in predictions_map:
                                    option = predictions_map[option_id]
                                    if option['class'] == 'checkbox_option' and self._is_contained_within(option, element):
                                        option_checkboxes = []
                                        for checkbox_id in element_ids:
                                            if checkbox_id in predictions_map:
                                                checkbox = predictions_map[checkbox_id]
                                                if checkbox['class'] == 'checkbox' and self._is_contained_within(checkbox, option):
                                                    option_checkboxes.append({
                                                        'type': 'checkbox',
                                                        'text': cleaned_text.get(checkbox_id, checkbox.get('text', '')),
                                                        'confidence': checkbox.get('confidence', 0.0),
                                                        'detection_id': checkbox_id
                                                    })
                                        context_options.append({
                                            'type': 'checkbox_option',
                                            'text': cleaned_text.get(option_id, option.get('text', '')),
                                            'confidence': option.get('confidence', 0.0),
                                            'detection_id': option_id,
                                            'checkboxes': option_checkboxes
                                        })
                            checkbox_contexts.append({
                                'type': 'checkbox_context',
                                'text': cleaned_text.get(element_id, element.get('text', '')),
                                'confidence': element.get('confidence', 0.0),
                                'detection_id': element_id,
                                'options': context_options
                            })
                
                # Then, add any fields that are spatially contained within this section but not yet assigned
                section_elem = predictions_map[section_id]
                for pred in original_predictions:
                    if (pred['class'] == 'field' and 
                        pred['detection_id'] not in fields_in_tables and 
                        pred['detection_id'] not in [f['detection_id'] for f in fields] and
                        self._is_contained_within(pred, section_elem)):
                        fields.append({
                            'width': pred.get('width', 0.0),
                            'height': pred.get('height', 0.0),
                            'x': pred.get('x', 0.0),
                            'y': pred.get('y', 0.0),
                            'confidence': pred.get('confidence', 0.0),
                            'class_id': pred.get('class_id', 0),
                            'class': pred.get('class', ''),
                            'detection_id': pred['detection_id'],
                            'parent_id': pred.get('parent_id', ''),
                            'filename': pred.get('filename', ''),
                            'text': cleaned_text.get(pred['detection_id'], pred.get('text', ''))
                        })
                
                # Create enhanced section entry with cleaned text
                enhanced_structure[section_id] = {
                    'width': section_data.get('width', 0.0),
                    'height': section_data.get('height', 0.0),
                    'x': section_data.get('x', 0.0),
                    'y': section_data.get('y', 0.0),
                    'confidence': section_data.get('confidence', 0.0),
                    'class_id': section_data.get('class_id', 0),
                    'class': section_data.get('class', ''),
                    'detection_id': section_id,
                    'parent_id': section_data.get('parent_id', ''),
                    'filename': section_data.get('filename', ''),
                    'text': cleaned_text.get(section_id, section_data.get('text', '')),
                    'fields': fields,
                    'tables': tables,
                    'checkbox_contexts': checkbox_contexts
                }
            
            return enhanced_structure
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return structure

    def process(self, predictions_file: str, output_file: str):
        """Process the OCR predictions and create a structured document."""
        # Load predictions
        with open(predictions_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
        
        # Build initial hierarchy
        structure = self._build_hierarchy(predictions)
        
        # Enhance with LLM, passing original predictions
        enhanced_structure = self._enhance_structure_with_llm(structure, predictions)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_structure, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Document structure saved to {output_file}")


def main():
    # Create output directory if it doesn't exist
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    # Default paths relative to script location
    default_input = output_dir / "ocr_enriched_predictions.json"
    default_output = output_dir / "document_structure.json"

    parser = argparse.ArgumentParser(description='Process document structure from OCR predictions')
    parser.add_argument('--input', default=str(default_input),
                      help='Path to OCR enriched predictions JSON')
    parser.add_argument('--output', default=str(default_output),
                      help='Path to save the structured output')
    
    args = parser.parse_args()
    
    try:
        structurer = DocumentStructurer()
        structurer.process(args.input, args.output)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set your OpenAI API key using:")
        print("export OPENAI_API_KEY=your_api_key_here")
        exit(1)


if __name__ == "__main__":
    main()
    