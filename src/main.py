import argparse
import json # Add json import for saving tables
from snippet_extractor import SnippetExtractor
from snippet_ocr import SnippetOCR
from doc_structure import process_document, build_document_hierarchy, clean_empty_children
from table_extractor import extract_tables_from_document_structure # Import table extractor function
# Import table parser functions
from table_parser import process_tables, update_document_structure_with_processed_tables, merge_table_results_with_ocr
# Import document cleaning class
from clean_doc import CleanDoc

def main():
    parser = argparse.ArgumentParser(description="Run the document processing pipeline.")
    parser.add_argument("--image", default="./images/train8.jpg", help="Path to input image")
    parser.add_argument("--output", default="./snippets", help="Where to save cropped snippets")
    parser.add_argument("--api_key", default="eBaGauw8J2VV1q04yRhD", help="Roboflow API key")
    parser.add_argument("--workspace", default="cred", help="Roboflow workspace name")
    parser.add_argument("--workflow", default="detect-count-and-visualize-2", help="Workflow ID to run")
    parser.add_argument("--structured_output", default="./output/document_structure.json", help="Path to save the initial structured document")
    parser.add_argument("--extracted_tables_output", default="./output/extracted_tables.json", help="Path to save the extracted tables") 
    # Add arguments for table parsing outputs
    parser.add_argument("--processed_tables_output", default="./output/processed_tables.json", help="Path to save the processed tables") 
    parser.add_argument("--final_output", default="./output/final_structured_document.json", help="Path to save the final document structure before cleaning") 
    parser.add_argument("--enriched_predictions_output", default="./output/ocr_enriched_predictions_processed.json", help="Path to save the OCR enriched predictions")
    parser.add_argument("--merged_predictions_output", default="./output/ocr_enriched_predictions_processed_with_context.json", help="Path to save the merged predictions with context")
    # Add argument for cleaned output
    parser.add_argument("--cleaned_output", default="./output/cleaned_document.json", help="Path to save the final cleaned document") 
    args = parser.parse_args()

    # --- Initialize variables --- 
    predictions = []
    ocr_enriched_predictions = []
    structured_document = None
    extracted_tables = {}
    processed_tables = {}
    final_structured_document = None
    cleaned_document = None

    print("🚀 Starting snippet extraction...")
    extractor = SnippetExtractor(
        image_path=args.image,
        output_dir=args.output,
        api_key=args.api_key,
        workspace_name=args.workspace,
        workflow_id=args.workflow
    )
    predictions = extractor.extract()
    print("✅ Snippet extraction complete.")    


    print("🚀 Starting snippet OCR...")
    ocr = SnippetOCR(
        snippet_dir=args.output,
        predictions=predictions 
    )
    # Capture the OCR results
    ocr_enriched_predictions = ocr.run()
    print("✅ Snippet OCR complete.")

    # --- Document Structuring Step ---
    print("🚀 Starting document structuring...")
    try:
        # Debug: Print the structure of OCR predictions
        print("OCR Predictions structure:")
        print(json.dumps(ocr_enriched_predictions[0] if ocr_enriched_predictions else {}, indent=2))
        
        # Convert OCR predictions to JSON string
        json_data = json.dumps(ocr_enriched_predictions)
        
        # Process the document using the new functions
        structured_document = process_document(json_data)
        
        # Build the document hierarchy
        doc_hierarchy = build_document_hierarchy(structured_document)
        
        # Clean any empty children from the hierarchy
        doc_hierarchy = clean_empty_children(doc_hierarchy)
        
        # Save the structured document
        try:
            with open(args.structured_output, "w", encoding="utf-8") as f:
                json.dump(doc_hierarchy, f, indent=2, ensure_ascii=False)
            print(f"✅ Structured document saved to {args.structured_output}")
        except IOError as e:
            print(f"Error saving structured document to {args.structured_output}: {e}")
            
        print("✅ Document structuring complete.")
    except Exception as e:
        print(f"❌ Error during document structuring: {e}")
        structured_document = None
        doc_hierarchy = None

    # --- Table Extraction Step ---
    if structured_document:
        print("🚀 Starting table extraction...")
        extracted_tables = extract_tables_from_document_structure(structured_document)
        print(f"ℹ️ Extracted {len(extracted_tables)} table(s).")
        
        # Save extracted tables to file
        try:
            with open(args.extracted_tables_output, "w", encoding="utf-8") as f:
                json.dump(extracted_tables, f, indent=2, ensure_ascii=False)
            print(f"✅ Extracted tables saved to {args.extracted_tables_output}")
        except IOError as e:
            print(f"Error saving extracted tables to {args.extracted_tables_output}: {e}")
            
        print("✅ Table extraction complete.")
    else:
        print("⚠️ Skipping table extraction because document structuring failed or returned no data.")
        extracted_tables = {} # Define as empty dict if skipped

    # --- Table Parsing Step ---
    if extracted_tables:
        print("🚀 Starting table parsing...")
        processed_tables = process_tables(extracted_tables)
        
        # Save processed tables to file
        try:
            with open(args.processed_tables_output, "w", encoding="utf-8") as f:
                json.dump(processed_tables, f, indent=2, ensure_ascii=False)
            print(f"✅ Processed tables saved to {args.processed_tables_output}")
        except IOError as e:
            print(f"Error saving processed tables to {args.processed_tables_output}: {e}")
        
        print("✅ Table parsing complete.")
        
        # --- Save OCR Enriched Predictions ---
        print("🚀 Saving OCR enriched predictions...")
        try:
            with open(args.enriched_predictions_output, "w", encoding="utf-8") as f:
                json.dump(ocr_enriched_predictions, f, indent=2, ensure_ascii=False)
            print(f"✅ OCR enriched predictions saved to {args.enriched_predictions_output}")
        except IOError as e:
            print(f"Error saving OCR enriched predictions to {args.enriched_predictions_output}: {e}")
        
        # --- Merge Table Results with OCR Predictions ---
        print("🚀 Merging table results with OCR predictions...")
        merged_predictions = merge_table_results_with_ocr(ocr_enriched_predictions, processed_tables)
        
        # Save merged predictions
        try:
            with open(args.merged_predictions_output, "w", encoding="utf-8") as f:
                json.dump(merged_predictions, f, indent=2, ensure_ascii=False)
            print(f"✅ Merged predictions saved to {args.merged_predictions_output}")
        except IOError as e:
            print(f"Error saving merged predictions to {args.merged_predictions_output}: {e}")
        
        print("✅ Table merging complete.")
        
        # --- Final Document Assembly Step ---
        print("🚀 Assembling final document...")
        final_structured_document = update_document_structure_with_processed_tables(
            doc_structure=structured_document, 
            processed_tables=processed_tables
        )
        
        # Save final structured document
        try:
            with open(args.final_output, "w", encoding="utf-8") as f:
                json.dump(final_structured_document, f, indent=2, ensure_ascii=False)
            print(f"✅ Final structured document saved to {args.final_output}")
        except IOError as e:
            print(f"Error saving final structured document to {args.final_output}: {e}")
            
        print("✅ Final document assembly complete.")

    else:
        print("⚠️ Skipping table parsing and final assembly because no tables were extracted.")
        # Use the initial structured document as the final if no tables
        final_structured_document = structured_document
        # Optionally, save the initial structured document as the final one if no tables exist
        # if structured_document:
        #      try:
        #          with open(args.final_output, "w", encoding="utf-8") as f:
        #              json.dump(structured_document, f, indent=2, ensure_ascii=False)
        #          print(f"✅ Final structured document (no tables processed) saved to {args.final_output}")
        #      except IOError as e:
        #          print(f"Error saving final structured document to {args.final_output}: {e}")

    # --- Document Cleaning Step ---
    if final_structured_document:
        print("🚀 Starting document cleaning...")
        cleaner = CleanDoc()
        cleaned_document = cleaner.clean_document(final_structured_document)
        
        # Save cleaned document
        try:
            cleaner.save_cleaned_document(cleaned_document, args.cleaned_output)
            print(f"✅ Cleaned document saved to {args.cleaned_output}")
        except IOError as e:
            print(f"Error saving cleaned document to {args.cleaned_output}: {e}")
            
        print("✅ Document cleaning complete.")
    else:
        print("⚠️ Skipping document cleaning because previous steps failed.")

    print("🎉 Pipeline finished!")

if __name__ == "__main__":
    main()
