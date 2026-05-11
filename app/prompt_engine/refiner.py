import json
import os
import yaml

_DEMO_MODE = False
try:
    from google import genai
except ImportError:
    _DEMO_MODE = True

from prompt_engine.builder import PromptBuilder
from prompt_engine.niche_loader import NicheLoader
from prompt_engine.image_analyzer import ImageAnalyzer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class PromptRefiner:
    def __init__(self, logger=None, config_path=None, demo_mode=None):
        self.builder = PromptBuilder()
        self.niche_loader = NicheLoader()
        self.logger = logger
        self.demo_mode = demo_mode

        if self.demo_mode is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            sa_path = None
            if config_path is None:
                config_path = os.path.join(_APP_DIR, "configs", "veo_config.yaml")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                sa_path = cfg.get("veo", {}).get("service_account_file", "")
                if not os.path.isabs(sa_path):
                    sa_path = os.path.join(os.path.dirname(config_path), sa_path)
            has_sa = sa_path and os.path.exists(sa_path) if sa_path else False
            self.demo_mode = not (bool(api_key) or has_sa)

        if self.demo_mode and self.logger:
            self.logger.info("DEMO MODE — tanpa LLM, menggunakan template langsung")

        if not self.demo_mode:
            if config_path is None:
                config_path = os.path.join(_APP_DIR, "configs", "veo_config.yaml")
            self._config_dir = os.path.dirname(os.path.abspath(config_path))

            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)["veo"]

            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                sa_path = self.config["service_account_file"]
                if not os.path.isabs(sa_path):
                    sa_path = os.path.join(self._config_dir, sa_path)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
                self.client = genai.Client(
                    vertexai=True,
                    project=self.config["project_id"],
                    location=self.config["location"]
                )

            self.model_id = self.config.get("llm_model_id", "gemini-1.5-flash-002")
            self.model_id_pro = self.config.get("llm_model_id_pro", "gemini-1.5-pro-002")
        else:
            self.client = None
            self.model_id = None
            self.model_id_pro = None

        self.max_iterations = 3

    def call_llm(self, prompt, use_pro=False):
        if self.demo_mode:
            raise RuntimeError("DEMO_MODE")
        response = self.client.models.generate_content(
            model=self.model_id_pro if use_pro else self.model_id,
            contents=prompt
        )
        return response.text

    def _demo_part_text(self, part_name, template_name, niche_profile, user_input):
        tpl = self.builder.load_template(template_name)
        lines = tpl.strip().split("\n")

        instructions = [l for l in lines if l.startswith("INSTRUCTIONS:") or l.startswith("- ")]
        parts = niche_profile.get(part_name, {})
        if isinstance(parts, dict):
            defaults = parts.get("camera_default") or parts.get("default") or parts.get("vocabulary", [])
            if isinstance(defaults, list):
                defaults = ", ".join(defaults[:3])
        elif isinstance(parts, str):
            defaults = parts
        else:
            defaults = str(parts) if parts else ""

        result = f"{part_name.replace('_', ' ').title()}: {user_input}"
        if defaults:
            result += f", using {defaults}"
        return result

    def _generate_part(self, template_name, niche_profile, user_input, image_analysis=None):
        if self.demo_mode:
            part_name = None
            for k, v in self.builder.get_template_names().items():
                if v == template_name:
                    part_name = k
                    break
            return self._demo_part_text(part_name or "cinematography", template_name, niche_profile, user_input)

        template = self.builder.load_template(template_name)
        has_ref = image_analysis is not None
        ref_hint = ""
        if has_ref:
            ref_hint = f"\n\nIMAGE ANALYSIS (do not redescribe these): {json.dumps(image_analysis.get('do_not_redescribe', []))}\nSUGGESTED MOTION: {json.dumps(image_analysis.get('suggested_motion', []))}"

        prompt = f"""{template}

NICHE PROFILE:
{json.dumps(niche_profile, indent=2)}

USER INTENT: {user_input}{ref_hint}"""
        return self.call_llm(prompt)

    def _evaluate_prompt(self, assembled_prompt, use_pro=True):
        if self.demo_mode:
            return 7, "Demo mode — tanpa evaluasi LLM", {"demo": True}

        eval_template = self.builder.load_template("h_prompt_evaluation.md")
        eval_prompt = f"""{eval_template}

PROMPT TO EVALUATE:
{assembled_prompt}"""
        try:
            text = self.call_llm(eval_prompt, use_pro=use_pro)
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            score = result.get("score", 0)
            feedback = result.get("feedback", "No feedback")
            breakdown = result.get("breakdown", {})
        except:
            score = 7
            feedback = "Evaluation parse failed, manual review recommended"
            breakdown = {}
        return score, feedback, breakdown

    def _get_negative(self, niche_profile, image_analysis=None):
        base_negative = niche_profile.get("negative", "")
        if image_analysis and image_analysis.get("do_not_redescribe"):
            extra = ", ".join(image_analysis["do_not_redescribe"][:5])
            base_negative += f", {extra}"
        return base_negative

    def refine_prompt(self, user_input, niche_slug=None, image_path=None):
        niche_profile = self.niche_loader.load(niche_slug) if niche_slug else self.niche_loader.load("property_tour")
        if not niche_profile:
            niche_profile = self.niche_loader.load("property_tour")

        image_analysis = None
        if image_path and not self.demo_mode:
            image_analyzer = ImageAnalyzer(self.client, self.model_id)
            image_analysis = image_analyzer.analyze(image_path)

        job_data = {
            "user_input": user_input,
            "niche": niche_slug or "property_tour",
            "has_image": image_path is not None,
            "iterations": []
        }

        best_prompt = None
        best_score = 0
        best_negative = self._get_negative(niche_profile, image_analysis)
        current_feedback = "Initial generation"

        iterations = 1 if self.demo_mode else self.max_iterations
        for iteration in range(1, iterations + 1):
            if self.logger:
                self.logger.info(f"{'[DEMO] ' if self.demo_mode else ''}Iterasi {iteration}...")

            parts = {}
            part_templates = {
                "cinematography": "a_cinematography.md",
                "subject": "b_subject.md",
                "action": "c_action.md",
                "context": "d_context.md",
                "style_audio": "e_style_audio.md",
            }

            for part_name, template_name in part_templates.items():
                try:
                    part_text = self._generate_part(
                        template_name, niche_profile, user_input, image_analysis
                    )
                    parts[part_name] = part_text.strip()
                except Exception as e:
                    parts[part_name] = ""
                    if self.logger:
                        self.logger.warning(f"Failed to generate {part_name}: {e}")

            assembled = self.builder.assemble_prompt(parts)

            score, feedback, breakdown = self._evaluate_prompt(
                assembled,
                use_pro=(iteration == self.max_iterations)
            )
            current_feedback = feedback

            job_data["iterations"].append({
                "iteration": iteration,
                "parts": parts,
                "assembled_prompt": assembled,
                "score": score,
                "feedback": feedback,
                "breakdown": breakdown,
            })

            if score > best_score:
                best_prompt = assembled
                best_score = score
                best_negative = self._get_negative(niche_profile, image_analysis)

            if score >= 9:
                break

            niche_profile_for_update = niche_profile.copy()
            niche_profile_for_update["feedback"] = feedback
            user_input += f"\nFeedback from previous iteration: {feedback}"

        result = self.builder.assemble_full(best_prompt, best_negative)
        result["score"] = best_score
        result["iterations"] = job_data["iterations"]

        if self.logger:
            job_id = self.logger.log_job({
                "user_input": user_input,
                "niche": niche_slug,
                "iterations": job_data["iterations"],
                "final_prompt": best_prompt,
                "final_negative": best_negative,
                "score": best_score
            })
            self.logger.info(f"Refinement complete. Job ID: {job_id}, Score: {best_score}")

        return result
