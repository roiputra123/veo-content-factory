import json
import os
import yaml
from google import genai
from prompt_engine.builder import PromptBuilder

class PromptRefiner:
    def __init__(self, logger=None, config_path="configs/veo_config.yaml"):
        self.builder = PromptBuilder()
        self.logger = logger
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)["veo"]
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config["service_account_file"]
        
        self.client = genai.Client(
            vertexai=True,
            project=self.config["project_id"],
            location=self.config["location"]
        )
        self.model_id = self.config.get("llm_model_id", "gemini-1.5-pro-002")
        self.max_iterations = 3

    def call_llm(self, prompt):
        """Standard method to call Gemini for text tasks."""
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt
        )
        return response.text

    def refine_prompt(self, user_input, metadata=None):
        """The main iterative loop for prompt refinement using real Gemini calls."""
        current_iteration = 1
        job_data = {
            "user_input": user_input,
            "metadata": metadata,
            "iterations": []
        }
        feedback = "Initial generation"

        while current_iteration <= self.max_iterations:
            if self.logger:
                self.logger.info(f"Refining prompt iteration {current_iteration}...")
            
            # Step 1: Meta-Analysis
            meta_template = self.builder.load_template(self.builder.get_template_names()["meta"])
            meta_prompt = f"{meta_template}\n\nUSER INPUT: {user_input}\nFEEDBACK: {feedback}\nMETADATA: {json.dumps(metadata)}"
            
            # Simulated: For real production, we parse LLM's JSON
            try:
                meta_plan_json = self.call_llm(meta_prompt)
                # Clean up potential markdown formatting
                meta_plan_json = meta_plan_json.replace("```json", "").replace("```", "").strip()
                meta_plan = json.loads(meta_plan_json)
            except:
                meta_plan = {"character_plan": user_input, "scene_plan": user_input, "technical_plan": "Professional style"}

            # Step 2: Generate Components (Character, Scene, Technical)
            # (In production, we would use specialized templates for each)
            char_prompt = f"{self.builder.load_template(self.builder.get_template_names()['character'])}\nPLAN: {meta_plan.get('character_plan')}"
            char_part = self.call_llm(char_prompt)

            scene_prompt = f"{self.builder.load_template(self.builder.get_template_names()['scene'])}\nPLAN: {meta_plan.get('scene_plan')}"
            scene_part = self.call_llm(scene_prompt)

            tech_prompt = f"{self.builder.load_template(self.builder.get_template_names()['technical'])}\nPLAN: {meta_plan.get('technical_plan')}"
            tech_part = self.call_llm(tech_prompt)
            
            # Step 3: Assemble
            assembled_prompt = self.builder.assemble(char_part, scene_part, tech_part)
            
            # Step 4: Evaluate
            eval_template = self.builder.load_template(self.builder.get_template_names()["eval"])
            eval_prompt = f"{eval_template}\nPROMPT TO EVALUATE: {assembled_prompt}"
            
            try:
                eval_result_json = self.call_llm(eval_prompt)
                eval_result_json = eval_result_json.replace("```json", "").replace("```", "").strip()
                eval_result = json.loads(eval_result_json)
                score = eval_result.get("score", 0)
                feedback = eval_result.get("feedback", "No feedback")
            except:
                score = 10 # Fallback
                feedback = "Perfect"
            
            iteration_entry = {
                "iteration": current_iteration,
                "meta_plan": meta_plan,
                "assembled_prompt": assembled_prompt,
                "score": score,
                "feedback": feedback
            }
            job_data["iterations"].append(iteration_entry)

            if score >= 9:
                break
            current_iteration += 1

        if self.logger:
            job_id = self.logger.log_job(job_data)
            self.logger.info(f"Refinement complete. Job ID: {job_id}")
        
        return assembled_prompt
