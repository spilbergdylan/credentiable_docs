import os
import time
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR

def run_debug_ocr(snippet_path):
    print(f"\n🔍 Loading snippet image from: {snippet_path}")
    image = Image.open(snippet_path)
    print(f"📐 Image size: {image.size}, mode: {image.mode}")
    
    image_np = np.array(image)

    print("⚙️  Initializing PaddleOCR...")
    start_init = time.time()
    ocr = PaddleOCR(use_angle_cls=False, lang='en', show_log=True)
    print(f"✅ PaddleOCR initialized in {time.time() - start_init:.2f} seconds")

    # Warm-up with dummy image
    print("🔥 Running warm-up OCR...")
    dummy = np.ones((32, 100, 3), dtype=np.uint8) * 255
    start_warm = time.time()
    _ = ocr.ocr(dummy, cls=False)
    print(f"✅ Warm-up completed in {time.time() - start_warm:.2f} seconds")

    print("\n🚀 Running real OCR...")
    start_ocr = time.time()
    result = ocr.ocr(image_np, cls=False)
    elapsed = time.time() - start_ocr

    if result and result[0]:
        text = result[0][0][1][0]
    else:
        text = ""

    print(f"📝 OCR Result: {repr(text)}")
    print(f"⏱️  OCR took {elapsed:.2f} seconds")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("snippet", help="Path to a single snippet image")
    args = parser.parse_args()

    run_debug_ocr(args.snippet)
