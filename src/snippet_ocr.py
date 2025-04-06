import os
import json
import time
from PIL import Image, ImageOps, ImageEnhance
from paddleocr import PaddleOCR
import numpy as np
import traceback
import pytesseract


class SnippetOCR:
    def __init__(self, snippet_dir, predictions):
        self.snippet_dir = snippet_dir
        self.predictions = predictions
        # Initialize PaddleOCR with more conservative memory settings
        self.ocr = PaddleOCR(
            use_angle_cls=False,
            lang='en',
            show_log=False,
            use_gpu=False  # Force CPU usage to avoid memory issues
        )
        # Keep track of images that fail with PaddleOCR
        self.paddle_failed_images = set()

    def preprocess(self, image):
        # Resize large images to prevent memory issues
        max_size = 800  # Reduced from 1024 to be more conservative
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to grayscale and enhance contrast
        gray = image.convert("L")
        contrasted = ImageEnhance.Contrast(gray).enhance(2.0)
        inverted = ImageOps.invert(contrasted)
        return inverted

    def process_with_paddle(self, image_np):
        """Process image with PaddleOCR"""
        result = self.ocr.ocr(image_np, cls=False)
        return result[0][0][1][0] if result and result[0] else ""

    def process_with_tesseract(self, image):
        """Process image with Tesseract OCR"""
        # Tesseract works better with the original image or with different preprocessing
        # For sections, we'll use a different preprocessing approach
        gray = image.convert("L")
        # Increase contrast for better text recognition
        contrasted = ImageEnhance.Contrast(gray).enhance(2.5)
        # Use Tesseract with specific configuration for better results
        text = pytesseract.image_to_string(contrasted, config='--psm 6 --oem 3')
        return text.strip()

    def run(self):
        filename_to_pred = {pred['filename']: pred for pred in self.predictions if 'filename' in pred}
        files = [f for f in os.listdir(self.snippet_dir) if f.lower().endswith(".png") and f in filename_to_pred]

        for idx, filename in enumerate(files):
            print(f"\n➡️  [{idx+1}/{len(files)}] Processing {filename}...", flush=True)

            try:
                pred = filename_to_pred[filename]
                path = os.path.join(self.snippet_dir, filename)
                image = Image.open(path)
                
                # Determine if this is a section image
                is_section = filename.startswith("section_")
                
                # If this image previously failed with PaddleOCR, use Tesseract directly
                if filename in self.paddle_failed_images:
                    print("📄 Using Tesseract (previously failed with PaddleOCR)", flush=True)
                    start = time.time()
                    text = self.process_with_tesseract(image)
                    elapsed = time.time() - start
                elif is_section:
                    # Use Tesseract for section images
                    print("📄 Using Tesseract for section image", flush=True)
                    start = time.time()
                    text = self.process_with_tesseract(image)
                    elapsed = time.time() - start
                else:
                    # Try PaddleOCR for other images
                    print("📄 Using PaddleOCR for field image", flush=True)
                    try:
                        processed = self.preprocess(image)
                        image_np = np.array(processed)
                        
                        start = time.time()
                        text = self.process_with_paddle(image_np)
                        elapsed = time.time() - start
                    except Exception as paddle_error:
                        print(f"⚠️ PaddleOCR failed: {str(paddle_error)}", flush=True)
                        print("🔄 Falling back to Tesseract OCR", flush=True)
                        # Add to failed images set
                        self.paddle_failed_images.add(filename)
                        # Try with Tesseract
                        start = time.time()
                        text = self.process_with_tesseract(image)
                        elapsed = time.time() - start
                
                pred["text"] = text
                print(f"🔍 OCR result: {repr(text)}", flush=True)
                print(f"⏱️  Took {elapsed:.2f} seconds", flush=True)

            except Exception as e:
                print(f"❌ Error processing {filename}: {str(e)}", flush=True)
                print(traceback.format_exc(), flush=True)
                # Set empty text for failed OCR attempts
                pred["text"] = ""

        return self.predictions


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--snippets", default="snippets", help="Directory of snippet images")
    parser.add_argument("--predictions", default="./output/predictions.json", help="Original predictions JSON file")
    parser.add_argument("--output", default="./output/ocr_enriched_predictions.json", help="Path to save enriched predictions")
    args = parser.parse_args()

    with open(args.predictions, "r", encoding="utf-8") as f:
        predictions = json.load(f)

    ocr = SnippetOCR(args.snippets, predictions)
    enriched = ocr.run()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"✅ Enriched predictions saved to {args.output}")


if __name__ == "__main__":
    main()
