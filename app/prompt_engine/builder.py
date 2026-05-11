import os

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

class PromptBuilder:
    def __init__(self, templates_dir=None):
        self.templates_dir = templates_dir or _TEMPLATES_DIR

    def load_template(self, filename):
        path = os.path.join(self.templates_dir, filename)
        with open(path, 'r') as f:
            return f.read()

    def get_template_names(self):
        return {
            "cinematography": "a_cinematography.md",
            "subject": "b_subject.md",
            "action": "c_action.md",
            "context": "d_context.md",
            "style_audio": "e_style_audio.md",
            "negative": "f_negative.md",
            "eval": "h_prompt_evaluation.md",
        }

    def assemble_prompt(self, parts):
        result = parts.get("cinematography", "")
        if parts.get("subject"):
            result += "\n\n" + parts["subject"]
        if parts.get("action"):
            result += "\n\n" + parts["action"]
        if parts.get("context"):
            result += "\n\n" + parts["context"]
        if parts.get("style_audio"):
            result += "\n\n" + parts["style_audio"]
        return result.strip()

    def assemble_full(self, positive, negative=None):
        result = {"positive": positive}
        if negative:
            result["negative"] = negative
        return result
