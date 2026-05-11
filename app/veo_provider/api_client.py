import os
import time
import yaml
from google import genai
from google.genai import types

class VeoClient:
    def __init__(self, config_path="configs/veo_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)["veo"]

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config["service_account_file"]

        self.client = genai.Client(
            vertexai=True,
            project=self.config["project_id"],
            location=self.config["location"]
        )

        mode = self.config.get("mode", "lite")
        self.model_id = self.config["model_ids"].get(mode, self.config["model_ids"]["lite"])
        self.default_config = self.config["default_config"]

    def generate_video(self, prompt, source_image_path=None, output_filename=None):
        if not output_filename:
            output_filename = f"storage/results/video_{int(time.time())}.mp4"

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)

        try:
            image_obj = None
            if source_image_path and os.path.exists(source_image_path):
                image_obj = types.Image.from_file(source_image_path)

            negative_prompt = None
            if isinstance(prompt, dict):
                negative_prompt = prompt.get("negative")
                prompt = prompt.get("positive", "")

            gen_config = types.GenerateVideosConfig(
                aspect_ratio=self.default_config.get("aspect_ratio", "16:9"),
                duration_seconds=self.default_config.get("duration_seconds", 5),
                enhance_prompt=self.default_config.get("enhance_prompt", True),
            )

            operation = self.client.models.generate_videos(
                model=self.model_id,
                prompt=prompt,
                image=image_obj,
                config=gen_config,
            )

            print(f"Video generation started: {operation.name} (model: {self.model_id})")
            print(f"Prompt: {prompt[:100]}...")
            if negative_prompt:
                print(f"Negative: {negative_prompt[:100]}...")
            print("Polling for results...")

            while not operation.done:
                time.sleep(30)
                operation = self.client.operations.get(operation)
                print(".", end="", flush=True)

            if operation.response:
                video_data = operation.response.generated_videos[0].video.data
                with open(output_filename, "wb") as f:
                    f.write(video_data)
                print(f"\nSuccess! Video saved to: {output_filename}")
                return output_filename
            else:
                print(f"\nGeneration failed: {operation.error}")
                return None

        except Exception as e:
            print(f"\nFatal error in VeoClient: {str(e)}")
            return None

    def estimate_cost(self, duration_seconds=None):
        mode = self.config.get("mode", "lite")
        audio = self.config.get("default_config", {}).get("generate_audio", False)
        prices = {
            "lite": {"no_audio": 0.03, "audio": 0.05},
            "fast": {"no_audio": 0.08, "audio": 0.10},
            "standard": {"no_audio": 0.20, "audio": 0.40},
        }
        dur = duration_seconds or self.default_config.get("duration_seconds", 5)
        price = prices.get(mode, prices["lite"])
        rate = price["audio"] if audio else price["no_audio"]
        return round(dur * rate, 2)
