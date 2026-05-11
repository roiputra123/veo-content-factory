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
        
    def generate_video(self, prompt, source_image_path=None, output_filename=None):
        """Generates a video from a prompt and an optional reference image."""
        if not output_filename:
            output_filename = f"storage/results/video_{int(time.time())}.mp4"
            
        try:
            image_obj = None
            if source_image_path and os.path.exists(source_image_path):
                # Using official from_file method as seen in research
                image_obj = types.Image.from_file(source_image_path)

            operation = self.client.models.generate_videos(
                model=self.config["model_id"],
                prompt=prompt,
                image=image_obj,
                config=types.GenerateVideosConfig(
                    aspect_ratio=self.config["default_config"]["aspect_ratio"],
                    duration_seconds=self.config["default_config"]["duration_seconds"],
                    enhance_prompt=self.config["default_config"]["enhance_prompt"]
                )
            )

            print(f"Video generation started: {operation.name}")
            print("Polling for results (this may take a few minutes)...")

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
