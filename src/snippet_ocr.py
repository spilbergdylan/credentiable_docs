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
        self.ocr = PaddleOCR(  
            use_angle_cls=True,
            lang='en',
            show_log=False,
            use_gpu=False
        )
        self.paddle_failed_images = set() # keep track of images that fail with PaddleOCR

    def preprocess_image(self, image, contrast_factor=2.0, threshold=None, invert=False):
        """
        Unified image preprocessing method.
        
        Args:
            image: PIL Image to process
            contrast_factor: Factor to enhance contrast (default: 2.0)
            threshold: Optional threshold for binary conversion (default: None)
            invert: Whether to invert the image colors (default: False)
        """
        max_size = 800
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        gray = image.convert("L")
        contrasted = ImageEnhance.Contrast(gray).enhance(contrast_factor)
        if threshold is not None:
            contrasted = contrasted.point(lambda x: 255 if x > threshold else 0)
        if invert:
            contrasted = ImageOps.invert(contrasted)
        return contrasted

    def process_with_paddle(self, image_np):
        result = self.ocr.ocr(image_np, cls=False)
        return result[0][0][1][0] if result and result[0] else ""

    def clean_section_text(self, text):
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return ""
            
        title = lines[0]
        title = title.replace('|', '')  
        title = title.replace('[', '').replace(']', '') 
        title = title.replace('{', '').replace('}', '')  
        title = title.replace('_', ' ') 
        title = ' '.join(title.split())
        title = title.title()
        
        return title

    def process_with_tesseract(self, image, is_section=False, is_title=False):
        """Process image with Tesseract OCR"""
        if is_section:
            processed = self.preprocess_image(image, contrast_factor=3.0, threshold=200)
            text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,/-() ')
            text = self.clean_section_text(text)
        elif is_title:
            processed = self.preprocess_image(image, contrast_factor=3.5, threshold=180)
            text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,/-() ')
            text = self.clean_section_text(text)  # Reuse the same cleaning function
        else:
            processed = self.preprocess_image(image, contrast_factor=2.5)
            text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3')
            text = text.strip()
        
        return text

    def run(self):
        filename_to_pred = {pred['filename']: pred for pred in self.predictions if 'filename' in pred}
        files = [f for f in os.listdir(self.snippet_dir) if f.lower().endswith(".png") and f in filename_to_pred]

        for idx, filename in enumerate(files):
            print(f"\n [{idx+1}/{len(files)}] Processing {filename}...", flush=True)

            try:
                pred = filename_to_pred[filename]
                path = os.path.join(self.snippet_dir, filename)
                image = Image.open(path)
                is_section = filename.startswith("section_") # Here im determining if the image is a section or a title, they require different preprocessing
                is_title = filename.startswith("title_")
                
                # If this image previously failed with PaddleOCR, use Tesseract directly
                if filename in self.paddle_failed_images:
                    print("Using Tesseract (previously failed with PaddleOCR)", flush=True)
                    start = time.time()
                    text = self.process_with_tesseract(image, is_section, is_title)
                    elapsed = time.time() - start
                elif is_section or is_title:
                    print(f"Using Tesseract for {'section' if is_section else 'title'} image", flush=True)
                    start = time.time()
                    text = self.process_with_tesseract(image, is_section, is_title)
                    elapsed = time.time() - start
                else:
                    print("Using PaddleOCR for field image", flush=True)
                    try:
                        processed = self.preprocess_image(image, invert=True)
                        image_np = np.array(processed)
                        
                        start = time.time()
                        text = self.process_with_paddle(image_np)
                        elapsed = time.time() - start
                    except Exception as paddle_error:
                        print(f"PaddleOCR failed: {str(paddle_error)}", flush=True)
                        print("Falling back to Tesseract OCR", flush=True)
                        self.paddle_failed_images.add(filename)
                        start = time.time()
                        text = self.process_with_tesseract(image, is_section, is_title) # if PaddleOCR fails, use Tesseract
                        elapsed = time.time() - start 
                
                pred["text"] = text
                print(f"OCR result: {repr(text)}", flush=True)
                print(f"Took {elapsed:.2f} seconds", flush=True)

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}", flush=True)
                print(traceback.format_exc(), flush=True)
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

    print(f"Enriched predictions saved to {args.output}")


if __name__ == "__main__":
    main()
