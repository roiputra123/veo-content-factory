import os

class PromptBuilder:
    def __init__(self, templates_dir="prompt_engine/templates"):
        self.templates_dir = templates_dir
    
    def load_template(self, filename):
        path = os.path.join(self.templates_dir, filename)
        with open(path, 'r') as f:
            return f.read()

    def assemble(self, character_part, scene_part, technical_part):
        """Assembles components into a final professional Veo 3 prompt."""
        # This can be expanded to follow the 8-component structure more strictly
        return f"{character_part}\n\n{scene_part}\n\n{technical_part}"

    def get_template_names(self):
        return {
            "meta": "b_meta_analysis.md",
            "character": "c_character_development.md",
            "scene": "d_scene_architecture.md",
            "technical": "e_technical_specification.md",
            "eval": "h_prompt_evaluation.md"
        }
