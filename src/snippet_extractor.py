import os
import json
import base64
import shutil
from PIL import Image
from inference_sdk import InferenceHTTPClient


class SnippetExtractor:
    def __init__(self, image_path, output_dir, api_key, workspace_name, workflow_id):
        self.image_path = image_path
        self.output_dir = output_dir
        self.api_key = api_key
        self.workspace_name = workspace_name
        self.workflow_id = workflow_id

        os.makedirs(self.output_dir, exist_ok=True)

        self.client = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=self.api_key
        )

    def _clear_output_directory(self):
        """Clear the output directory before generating new snippets."""
        if os.path.exists(self.output_dir):
            print(f"🗑️ Clearing existing snippets in {self.output_dir}")
            shutil.rmtree(self.output_dir)
            os.makedirs(self.output_dir)
            print("✅ Output directory cleared")

    def extract(self):
        # Clear existing snippets before generating new ones
        self._clear_output_directory()
        
        print("📤 Sending image to Roboflow...")
        with open(self.image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        results = self.client.run_workflow(
            workspace_name=self.workspace_name,
            workflow_id=self.workflow_id,
            images={"image": image_data},
            use_cache=True
        )

        result = results[0]
        predictions_wrapper = result.get("predictions", {})
        predictions = predictions_wrapper.get("predictions", [])

        print(f"✅ Received {len(predictions)} predictions")

        if not predictions:
            print("❌ No valid predictions found.")
            return

        original_image = Image.open(self.image_path).convert("RGB")
        print("Original image size:", original_image.size)
        print("🧪 Using original input image:", self.image_path)

        model_input = predictions_wrapper.get("image", {})
        model_w = model_input.get("width", 640)
        model_h = model_input.get("height", 640)
        print("Roboflow input size:", model_input)

        enriched_predictions = []

        for pred in predictions:
            if pred.get("class") in ["field", "checkbox_context", "section", "table","checkbox","checkbox_option"]:
                filename = self._save_snippet(original_image, pred, (model_w, model_h))
                if filename:
                    pred["filename"] = filename
                    enriched_predictions.append(pred)

        # Create output directory if it doesn't exist
        os.makedirs("./output", exist_ok=True)

        with open("./output/predictions.json", "w", encoding="utf-8") as f:
            json.dump(enriched_predictions, f, indent=2, ensure_ascii=False)

        print("✅ Saved predictions to predictions.json")

    def _save_snippet(self, image, pred, model_input_size):
        img_w, img_h = image.size
        model_w, model_h = model_input_size

        scale_x = img_w / model_w
        scale_y = img_h / model_h

        x = float(pred["x"]) * scale_x
        y = float(pred["y"]) * scale_y
        w = float(pred["width"]) * scale_x
        h = float(pred["height"]) * scale_y

        left   = int(x - w / 2)
        top    = int(y - h / 2)
        right  = int(x + w / 2)
        bottom = int(y + h / 2)
        box = (left, top, right, bottom)

        if left < 0 or top < 0 or right > img_w or bottom > img_h:
            print(f"⚠️ Skipping out-of-bounds box: {box}")
            return None

        snippet = image.crop(box)
        filename = f"{pred['class']}_{pred['detection_id']}.png"
        snippet.save(os.path.join(self.output_dir, filename))
        print(f"🖼 Saved: {filename}")
        return filename


# -----------------------
# CLI entry point
# -----------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output", default="../snippets", help="Where to save cropped snippets")
    parser.add_argument("--api_key", required=True, help="Roboflow API key")
    parser.add_argument("--workspace", required=True, help="Roboflow workspace name")
    parser.add_argument("--workflow", required=True, help="Workflow ID to run")
    args = parser.parse_args()

    extractor = SnippetExtractor(
        image_path=args.image,
        output_dir=args.output,
        api_key=args.api_key,
        workspace_name=args.workspace,
        workflow_id=args.workflow
    )
    extractor.extract()
    print("✅ Done")


if __name__ == "__main__":
    main()

        # python ./src/snippet_extractor.py \
        #     --image ./images/train4.jpg \
        #     --output ./snippets \
        #     --api_key "eBaGauw8J2VV1q04yRhD" \
        #     --workspace "cred" \
        #     --workflow "detect-count-and-visualize-2"