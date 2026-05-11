import json
import os

class ImageAnalyzer:
    def __init__(self, llm_client, model_id="gemini-1.5-flash-002"):
        self.client = llm_client
        self.model_id = model_id

    def analyze(self, image_path):
        if not image_path or not os.path.exists(image_path):
            return None

        import PIL.Image
        img = PIL.Image.open(image_path)

        prompt = """Analyze this reference image for video generation. Output JSON only:

{
  "existing_elements": {
    "subject": "main subject description",
    "camera_position": "where camera is relative to subject",
    "lighting": "lighting conditions",
    "environment": "background and surroundings",
    "colors": "dominant colors"
  },
  "do_not_redescribe": ["list of elements already in image"],
  "suggested_motion": ["what could move or change"]
}"""

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, img]
        )

        try:
            text = response.text
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except:
            return {
                "existing_elements": {
                    "subject": "unknown",
                    "camera_position": "unknown",
                    "lighting": "unknown",
                    "environment": "unknown",
                    "colors": "unknown"
                },
                "do_not_redescribe": [],
                "suggested_motion": ["gentle camera motion"]
            }
