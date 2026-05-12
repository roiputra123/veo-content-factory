import json
import os
import time
import yaml

_DEMO_MODE = False
try:
    from google import genai
    from google.genai import errors as genai_errors
except ImportError:
    _DEMO_MODE = True

from prompt_engine.builder import PromptBuilder
from prompt_engine.niche_loader import NicheLoader
from prompt_engine.image_analyzer import ImageAnalyzer
from llm_provider import LLMProvider

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
        self.llm = None
        self.client = None
        self.model_id = None
        self.model_id_pro = None

        if config_path is None:
            config_path = os.path.join(_APP_DIR, "configs", "veo_config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)["veo"]
            self._config_dir = os.path.dirname(os.path.abspath(config_path))
        else:
            self.config = None
            self._config_dir = None

        if self.demo_mode is None:
            self._try_init_providers()
            if self.demo_mode is None:
                self.demo_mode = not (self.client or self.llm)

        if self.demo_mode and self.logger:
            self.logger.info("DEMO MODE — tanpa LLM, menggunakan template langsung")

        self.max_iterations = int(os.environ.get("LLM_ITERATIONS", "3"))
        self.lang = os.environ.get("LANG", "id").lower()
        self.id_to_en = os.environ.get("ID_TO_EN", "true" if self.lang == "id" else "false").lower() in ("1", "true", "yes")

    def _try_init_providers(self):
        provider = os.environ.get("LLM_PROVIDER", "").lower()

        sa_path = None
        if self.config:
            sa_path = self.config.get("service_account_file", "")
            if sa_path and not os.path.isabs(sa_path):
                sa_path = os.path.join(self._config_dir, sa_path) if self._config_dir else sa_path
            sa_path = sa_path if (sa_path and os.path.exists(sa_path)) else None

        # Respect explicit LLM_PROVIDER set by user
        if provider == "openrouter":
            self._init_openrouter()
            if self.llm:
                return
        elif provider == "ollama":
            self._init_ollama()
            if self.llm:
                return
        elif provider == "gemini":
            self._init_gemini_api()
            if self.client:
                return

        # Auto-detect
        if not provider or provider == "auto":
            if self._init_gemini_api():
                return
            if sa_path and self._init_vertex(sa_path):
                return
            if self._init_openrouter():
                return
            if self._init_ollama():
                return

        self.demo_mode = True

    def _init_gemini_api(self):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("VERTEX_API_KEY")
        if not api_key:
            return False
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_id = (self.config or {}).get("llm_model_id", "gemini-2.0-flash")
            self.model_id_pro = (self.config or {}).get("llm_model_id_pro", "gemini-2.5-pro-preview")
            # Health check: detect quota exhaustion at init time
            try:
                self.client.models.count_tokens(model=self.model_id, contents="ok")
            except Exception as e:
                err = str(e)
                if "RESOURCE_EXHAUSTED" in err or "quota" in err.lower() or "429" in err:
                    if self.logger:
                        self.logger.warning(f"Gemini quota exhausted, skip: {err[:80]}")
                    self.client = None
                    return False
            if self.client and self.logger:
                self.logger.info(f"Gemini: {self.model_id}")
            return self.client is not None
        except Exception as e:
            self.client = None
            if self.logger:
                self.logger.warning(f"Gagal init Gemini API: {e}")
            return False

    def _init_vertex(self, sa_path):
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
            self.client = genai.Client(
                vertexai=True,
                project=self.config["project_id"],
                location=self.config.get("location", "us-central1")
            )
            self.model_id = self.config.get("llm_model_id", "gemini-2.0-flash")
            self.model_id_pro = self.config.get("llm_model_id_pro", "gemini-2.5-pro-preview")
            if self.logger:
                self.logger.info("Vertex AI via service account")
            return True
        except Exception as e:
            self.client = None
            if self.logger:
                self.logger.warning(f"Gagal init Vertex: {e}")
            return False

    def _init_openrouter(self):
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if not or_key:
            return False
        try:
            self.llm = LLMProvider(provider="openrouter",
                                   model=os.environ.get("LLM_MODEL", "openai/gpt-4o-mini"))
            self.demo_mode = False
            if self.logger:
                self.logger.info(f"OpenRouter: {self.llm.model}")
            return True
        except Exception as e:
            self.llm = None
            if self.logger:
                self.logger.warning(f"Gagal init OpenRouter: {e}")
            return False

    def _init_ollama(self):
        if not os.environ.get("OLLAMA_SSH_HOST"):
            return False
        try:
            self.llm = LLMProvider(provider="ollama")
            self.demo_mode = False
            if self.logger:
                self.logger.info(f"Ollama: {self.llm.host} model={self.llm.model}")
            return True
        except Exception as e:
            self.llm = None
            if self.logger:
                self.logger.warning(f"Gagal init Ollama: {e}")
            return False

    def call_llm(self, prompt, use_pro=False):
        if self.demo_mode:
            raise RuntimeError("DEMO_MODE")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._call_llm_once(prompt, use_pro)
            except Exception as e:
                err_str = str(e)
                is_rate_limit = (
                    "RESOURCE_EXHAUSTED" in err_str or
                    "429" in err_str or
                    "RATE_LIMITED" in err_str or
                    "quota" in err_str.lower()
                )
                if is_rate_limit and attempt < max_retries - 1:
                    delay = (2 ** attempt) * 10
                    if self.logger:
                        self.logger.warning(f"Rate limited, retry in {delay}s ({attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                raise

    def _call_llm_once(self, prompt, use_pro=False):
        if self.llm:
            temperature = 0.1 if use_pro else 0.3
            system = None
            if use_pro and self.llm.provider == "openrouter":
                system = "Anda adalah ahli prompt video berkualitas tinggi. Berikan respon dalam Bahasa Inggris."
            return self.llm.generate(prompt, temperature=temperature, system_prompt=system)

        model = self.model_id_pro if use_pro else self.model_id
        response = self.client.models.generate_content(
            model=model,
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

        lang_hint = "\n\nIMPORTANT: Respond in Bahasa Indonesia. Use rich Indonesian vocabulary for architectural and visual details."
        if self.lang == "en":
            lang_hint = "\n\nIMPORTANT: Respond in English. Use precise English cinematography terminology."

        prompt = f"""{template}{lang_hint}

NICHE PROFILE:
{json.dumps(niche_profile, indent=2)}

USER INTENT: {user_input}{ref_hint}"""
        return self.call_llm(prompt)

    def _convert_to_english(self, prompt_text):
        convert_template = self.builder.load_template("g_id_to_en.md")
        convert_prompt = convert_template.replace("{id_prompt}", prompt_text)
        en_prompt = self.call_llm(convert_prompt)
        return en_prompt.strip() if en_prompt and len(en_prompt) > 100 else prompt_text

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

        if self.demo_mode:
            iterations = 1
        elif self.llm and self.llm.provider == "ollama":
            iterations = min(2, self.max_iterations)
        elif self.llm:
            iterations = min(2, self.max_iterations)
        else:
            iterations = self.max_iterations
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

        # ID → EN conversion (convert Indonesian prompt to English for Veo 3)
        if best_prompt and self.id_to_en:
            try:
                en_prompt = self._convert_to_english(best_prompt)
                if self.logger:
                    self.logger.info(f"ID→EN: {len(best_prompt)} → {len(en_prompt)} chars")
                best_prompt = en_prompt
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"ID→EN conversion failed: {e}")

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
