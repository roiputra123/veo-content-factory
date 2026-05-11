import socket
import json
import logging

class SketchupBridge:
    def __init__(self, host="localhost", port=9876):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("SketchupBridge")

    def send_ruby(self, code):
        """Sends Ruby code to SketchUp and returns the result."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10.0)
                sock.connect((self.host, self.port))
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "eval_ruby",
                        "arguments": {"code": code}
                    },
                    "id": 1
                }
                
                sock.sendall(json.dumps(request).encode('utf-8') + b'\n')
                
                # Simple receive (can be improved for large responses)
                response_data = sock.recv(8192)
                response = json.loads(response_data.decode('utf-8'))
                
                if "error" in response:
                    raise Exception(response["error"].get("message", "Unknown error"))
                
                return response.get("result", {})
        except Exception as e:
            self.logger.error(f"Failed to communicate with SketchUp: {e}")
            return {"success": False, "error": str(e)}

    def get_model_info(self):
        """Extracts basic metadata from the active SketchUp model."""
        ruby_code = """
        model = Sketchup.active_model
        layers = model.layers.map { |l| l.name }
        materials = model.materials.map { |m| m.name }
        { 
          path: model.path, 
          layers: layers, 
          materials: materials,
          num_entities: model.entities.length 
        }.to_json
        """
        result = self.send_ruby(ruby_code)
        if "content" in result:
             # Extract the JSON string from the MCP response structure
             try:
                 text_content = result["content"][0]["text"]
                 return json.loads(text_content)
             except:
                 return result
        return result
