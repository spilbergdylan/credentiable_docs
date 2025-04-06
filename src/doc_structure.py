import json
from openai import OpenAI
import argparse
from typing import List, Dict, Any
import os
from pathlib import Path

class DocumentStructurer:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
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
            # Check if table is vertically close to section (within 100 pixels)
            vertical_proximity = 100
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Table starts near section bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Table ends near section top
                (e_top >= c_top and e_bottom <= c_bottom) or  # Table is fully within section vertically
                (e_top <= c_bottom and e_bottom >= c_top)     # Table overlaps with section
            )
            
            # Check if table has significant horizontal overlap with section
            horizontal_overlap = min(e_right, c_right) - max(e_left, c_left)
            min_horizontal_overlap = min(e_w, c_w) * 0.3  # 30% overlap
            
            return is_vertically_close and horizontal_overlap > min_horizontal_overlap
        
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
            # For checkboxes within checkbox_context, use a lower threshold (0.3 or 30% overlap)
            checkbox_threshold = 0.3
            
            # Calculate overlap
            overlap_width = min(e_right, c_right) - max(e_left, c_left)
            overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
            
            if overlap_width <= 0 or overlap_height <= 0:
                return False
                
            element_area = e_w * e_h
            overlap_area = overlap_width * overlap_height
            
            # Also check if checkbox is vertically close to its context
            vertical_proximity = 50  # pixels
            is_vertically_close = (
                abs(e_top - c_bottom) < vertical_proximity or  # Checkbox starts near context bottom
                abs(e_bottom - c_top) < vertical_proximity or  # Checkbox ends near context top
                (e_top >= c_top and e_bottom <= c_bottom)     # Checkbox is fully within context vertically
            )
            
            return is_vertically_close and (overlap_area / element_area) > checkbox_threshold
        
        # For other elements, use the original overlap calculation
        overlap_width = min(e_right, c_right) - max(e_left, c_left)
        overlap_height = min(e_bottom, c_bottom) - max(e_top, c_top)
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
            
        element_area = e_w * e_h
        overlap_area = overlap_width * overlap_height
        
        return (overlap_area / element_area) > threshold

    def _build_hierarchy(self, predictions: List[Dict]) -> Dict:
        """Build a hierarchical structure based on spatial relationships."""
        # Sort sections and other elements
        sections = [p for p in predictions if p['class'] == 'section']
        tables = [p for p in predictions if p['class'] == 'table']
        
        # Separate fields by type for better organization
        regular_fields = [p for p in predictions if p['class'] == 'field']
        checkbox_contexts = [p for p in predictions if p['class'] == 'checkbox_context']
        checkbox_options = [p for p in predictions if p['class'] == 'checkbox_option']
        checkboxes = [p for p in predictions if p['class'] == 'checkbox']
        
        print(f"\nFound {len(sections)} sections, {len(tables)} tables")
        print(f"Fields: {len(regular_fields)}, Checkbox contexts: {len(checkbox_contexts)}")
        print(f"Checkbox options: {len(checkbox_options)}, Checkboxes: {len(checkboxes)}")
        
        # Sort sections and tables by y-coordinate (top to bottom)
        sections.sort(key=lambda x: float(x['y']))
        tables.sort(key=lambda x: float(x['y']))
        
        document_structure = {
            'sections': {},
            'tables': {}
        }
        
        # Process each section
        for section in sections:
            section_id = section['detection_id']
            section_text = section.get('text', '').strip()
            
            # Find all elements contained within this section
            contained_fields = [
                field for field in regular_fields 
                if self._is_contained_within(field, section)
            ]
            
            contained_tables = [
                table for table in tables 
                if self._is_contained_within(table, section)
            ]
            
            # Find checkbox contexts in this section
            contained_checkbox_contexts = [
                context for context in checkbox_contexts 
                if self._is_contained_within(context, section)
            ]
            
            # Sort elements by y-coordinate
            contained_fields.sort(key=lambda x: float(x['y']))
            contained_tables.sort(key=lambda x: float(x['y']))
            contained_checkbox_contexts.sort(key=lambda x: float(x['y']))
            
            # Create section entry
            section_data = {
                'title': section_text,
                'fields': [],
                'tables': {},
                'checkbox_contexts': {}
            }
            
            # Add regular fields to section
            for field in contained_fields:
                field_data = {
                    'type': 'field',
                    'text': field.get('text', '').strip(),
                    'confidence': field.get('confidence', 0),
                    'detection_id': field['detection_id']
                }
                section_data['fields'].append(field_data)
            
            # Add tables to section
            for table in contained_tables:
                table_id = table['detection_id']
                table_text = table.get('text', '').strip()
                
                # Find fields contained within this table
                table_fields = [
                    field for field in regular_fields 
                    if self._is_contained_within(field, table)
                ]
                table_fields.sort(key=lambda x: float(x['y']))
                
                # Create table entry
                table_data = {
                    'type': 'table',
                    'text': table_text,
                    'confidence': table.get('confidence', 0),
                    'detection_id': table_id,
                    'fields': []
                }
                
                # Add fields to table
                for field in table_fields:
                    field_data = {
                        'type': 'field',
                        'text': field.get('text', '').strip(),
                        'confidence': field.get('confidence', 0),
                        'detection_id': field['detection_id']
                    }
                    table_data['fields'].append(field_data)
                
                section_data['tables'][table_id] = table_data
            
            # Process checkbox contexts and their hierarchy
            for context in contained_checkbox_contexts:
                context_id = context['detection_id']
                context_text = context.get('text', '').strip()
                
                # Find checkbox options in this context
                context_options = [
                    option for option in checkbox_options 
                    if self._is_contained_within(option, context)
                ]
                context_options.sort(key=lambda x: float(x['y']))
                
                # Create checkbox context entry
                context_data = {
                    'type': 'checkbox_context',
                    'text': context_text,
                    'confidence': context.get('confidence', 0),
                    'detection_id': context_id,
                    'checkbox_options': {}
                }
                
                # Process each checkbox option
                for option in context_options:
                    option_id = option['detection_id']
                    option_text = option.get('text', '').strip()
                    
                    # Find checkboxes in this option
                    option_checkboxes = [
                        checkbox for checkbox in checkboxes 
                        if self._is_contained_within(checkbox, option)
                    ]
                    option_checkboxes.sort(key=lambda x: float(x['y']))
                    
                    # Create checkbox option entry
                    option_data = {
                        'type': 'checkbox_option',
                        'text': option_text,
                        'confidence': option.get('confidence', 0),
                        'detection_id': option_id,
                        'checkboxes': []
                    }
                    
                    # Add checkboxes to option
                    for checkbox in option_checkboxes:
                        checkbox_data = {
                            'type': 'checkbox',
                            'text': checkbox.get('text', '').strip(),
                            'confidence': checkbox.get('confidence', 0),
                            'detection_id': checkbox['detection_id']
                        }
                        option_data['checkboxes'].append(checkbox_data)
                    
                    context_data['checkbox_options'][option_id] = option_data
                
                section_data['checkbox_contexts'][context_id] = context_data
            
            document_structure['sections'][section_id] = section_data
        
        # Process standalone tables (not contained within any section)
        for table in tables:
            table_id = table['detection_id']
            
            # Skip if table is already processed (contained within a section)
            if any(table_id in section['tables'] for section in document_structure['sections'].values()):
                continue
                
            table_text = table.get('text', '').strip()
            
            # Find fields contained within this table
            table_fields = [
                field for field in regular_fields 
                if self._is_contained_within(field, table)
            ]
            table_fields.sort(key=lambda x: float(x['y']))
            
            # Create standalone table entry
            table_data = {
                'type': 'table',
                'text': table_text,
                'confidence': table.get('confidence', 0),
                'detection_id': table_id,
                'fields': []
            }
            
            # Add fields to table
            for field in table_fields:
                field_data = {
                    'type': 'field',
                    'text': field.get('text', '').strip(),
                    'confidence': field.get('confidence', 0),
                    'detection_id': field['detection_id']
                }
                table_data['fields'].append(field_data)
            
            document_structure['tables'][table_id] = table_data
        
        return document_structure

    def _enhance_structure_with_llm(self, structure: Dict, original_predictions: List[Dict]) -> Dict:
        """Use GPT-3.5 to organize detection IDs into a logical structure."""
        # Convert structure to a string format for the LLM
        structure_str = json.dumps(structure, indent=2)
        
        prompt = f"""Given this document structure:
{structure_str}

Please analyze this structure and return a JSON object that contains only the detection_ids organized in a logical hierarchy.
The output should be a dictionary where:
- Keys are section detection_ids
- Values are arrays of field detection_ids that belong to that section
- Only include relevant fields and remove any noise
- Include all tables in the hierarchy
- a common structure is:
  - section
    - table
      - field
    - checkbox_context
      - checkbox_option
        - checkbox
Return only valid JSON with detection_ids, without any additional text."""

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a document structure analyzer that returns only valid JSON with detection_ids."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        try:
            # Get the organized detection IDs from LLM
            detection_structure = json.loads(response.choices[0].message.content)
            
            # Rebuild the full structure using the original predictions
            predictions_map = {p['detection_id']: p for p in original_predictions}
            enhanced_structure = {}
            
            for section_id, field_ids in detection_structure.items():
                if section_id not in predictions_map:
                    continue
                
                section = predictions_map[section_id]
                # Include all metadata from the original section
                section_data = section.copy()
                section_data['fields'] = []
                
                # Add fields based on the LLM-organized structure
                for field_id in field_ids:
                    if field_id in predictions_map:
                        field = predictions_map[field_id]
                        # Include all metadata from the original field
                        field_data = field.copy()
                        section_data['fields'].append(field_data)
                
                enhanced_structure[section_id] = section_data
            
            return enhanced_structure
        except json.JSONDecodeError:
            print("⚠️ LLM returned invalid JSON, using original structure")
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
    output_dir = Path("output")
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