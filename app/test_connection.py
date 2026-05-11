import os
import yaml
from google import genai

def test_connection(config_path="configs/veo_config.yaml"):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)["veo"]
        
        # Manually override to use vertex_key_production.json (x-victor)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "configs/vertex_key_production.json"
        
        client = genai.Client(
            vertexai=True,
            project="x-victor-470014-t7",
            location="us-central1"
        )
        
        # Testing with a very simple text call to check billing/auth
        print(f"Testing connection to project: x-victor-470014-t7...")
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say 'Connection Successful'"
        )
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
