import os
import yaml
import json
import datetime
from PIL import Image
from google import genai

class RenovatorFlow:
    def __init__(self, logger=None, config_path="configs/veo_config.yaml"):
        self.logger = logger
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)["veo"]
            
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config["service_account_file"]
            
            self.client = genai.Client(
                vertexai=True,
                project=self.config["project_id"],
                location=self.config["location"]
            )
            self.model_id = self.config.get("llm_model_id", "gemini-1.5-pro-002")
            self.api_available = True
        except Exception as e:
            if self.logger: self.logger.error(f"API Initialization failed: {e}")
            self.api_available = False

    def align_image(self, image_path, target_size=(1080, 1920)):
        """Ensures the image is exactly the target resolution."""
        try:
            img = Image.open(image_path)
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            img.save(image_path, "JPEG", quality=95)
            return True
        except Exception as e:
            if self.logger: self.logger.error(f"Image alignment failed for {image_path}: {e}")
            return False

    def save_log_to_docs(self, data, input_name):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"renovation_plan_{input_name.split('.')[0]}_{timestamp}.json"
        filepath = os.path.join("..", "docs", "prompts", filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        return filepath

    def run(self, input_image_name):
        if self.logger: self.logger.info(f"Running MULTI-STAGE Renovator Flow for: {input_image_name}")
        
        # Paths
        input_path = f"../assets/media/renovator/input/{input_image_name}"
        stages_dir = "../assets/media/renovator/stages/"
        os.makedirs(stages_dir, exist_ok=True)

        # Logic for 2 prompts for Veo3
        plan = {
            "stages": ["Abandoned (Stage 1)", "Under Construction (Stage 2)", "Final Design (Stage 3)"],
            "video_sequence": [
                {"from": "Stage 1", "to": "Stage 2", "prompt": ""},
                {"from": "Stage 2", "to": "Stage 3", "prompt": ""}
            ]
        }

        # Step 1: Analyze and Build Prompt A (Stage 1 -> 2)
        prompt_a = f"""
        TRANSITION A: Abandoned to Construction.
        Target: The derelict house in {input_image_name} being cleared.
        Action: Weeds disappear, debris is removed, scaffolding rises, and brick walls (tembok) start appearing.
        Camera: Static Frontal.
        Speed: Fast hyper-lapse.
        Style: Realistic architectural construction.
        """
        
        # Step 2: Analyze and Build Prompt B (Stage 2 -> 3)
        prompt_b = f"""
        TRANSITION B: Construction to Final.
        Target: The brick/concrete structure (tembok) becoming the finished luxury villa in {input_image_name}.
        Action: Plastering, painting, windows installation, lighting turning on, and landscaping completion.
        Camera: Static Frontal.
        Speed: Fast hyper-lapse.
        Style: Cinematic architectural film.
        """

        if self.api_available:
            try:
                plan["video_sequence"][0]["prompt"] = self.client.models.generate_content(model=self.model_id, contents=prompt_a).text
                plan["video_sequence"][1]["prompt"] = self.client.models.generate_content(model=self.model_id, contents=prompt_b).text
            except:
                plan["video_sequence"][0]["prompt"] = "Fallback Prompt A: Abandoned to Tembok."
                plan["video_sequence"][1]["prompt"] = "Fallback Prompt B: Tembok to Finished Villa."
        else:
            plan["video_sequence"][0]["prompt"] = "Fallback Prompt A: Abandoned to Tembok."
            plan["video_sequence"][1]["prompt"] = "Fallback Prompt B: Tembok to Finished Villa."

        # Step 3: Image Alignment (Stage 3)
        self.align_image(input_path)

        # Save the multi-stage plan
        saved_path = self.save_log_to_docs(plan, input_image_name)
        if self.logger:
            self.logger.info(f"Multi-stage plan saved to: {saved_path}")
            
        return f"SUCCESS: Generated 2-part transition sequence. Check docs/prompts for details."
