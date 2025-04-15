import json
import os
from table_parser import process_document_json, merge_table_results_with_ocr

# Define input and output file paths
extracted_tables_file = './output/extracted_tables.json'
processed_tables_file = './output/processed_tables.json'
base_predictions_file = './output/ocr_enriched_predictions_processed.json'  # Use the processed predictions as base
merged_output_file = './output/ocr_enriched_predictions_processed_with_context.json'  # New output with context

# Load the extracted tables
print(f"Loading extracted tables from {extracted_tables_file}...")
with open(extracted_tables_file, 'r') as f:
    extracted_tables = json.load(f)

# Process the tables
print(f"Processing tables with TableParser...")
processed_tables = process_document_json(extracted_tables)

# Save the processed tables
print(f"Saving processed tables to {processed_tables_file}...")
with open(processed_tables_file, 'w') as f:
    json.dump(processed_tables, f, indent=2)

# Load base predictions (already processed)
print(f"Loading base predictions from {base_predictions_file}...")
with open(base_predictions_file, 'r') as f:
    base_predictions = json.load(f)

# Merge the processed tables with base predictions
print(f"Merging processed tables with base predictions...")
merged_predictions = merge_table_results_with_ocr(base_predictions, processed_tables)

# Save the merged results
print(f"Saving merged predictions to {merged_output_file}...")
with open(merged_output_file, 'w') as f:
    json.dump(merged_predictions, f, indent=2)

print(f"Processing complete. Results saved to:")
print(f"- Processed tables: {processed_tables_file}")
print(f"- Merged predictions with context: {merged_output_file}") 