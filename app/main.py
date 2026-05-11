import os
import sys
import argparse
from core.logger import ProductionLogger

def main():
    parser = argparse.ArgumentParser(description="Evolutionary Construction Orchestrator (Veo 3)")
    parser.add_argument("--sync", action="store_true", help="Sync metadata from SketchUp")
    parser.add_argument("--build-prompt", action="store_true", help="Synthesize Veo 3 prompt from metadata")
    parser.add_argument("--generate", action="store_true", help="Execute video generation via Veo API")
    parser.add_argument("--renovate", type=str, help="Run the Renovation flow for a specific input image")
    parser.add_argument("--eval", type=str, help="Evaluate a specific Job ID")
    
    args = parser.parse_args()
    
    logger = ProductionLogger()
    logger.info("Evolutionary Construction Orchestrator initialized.")

    if args.renovate:
        from renovator_flow import RenovatorFlow
        print(f"[Special Flow] Starting Renovation Timelapse for: {args.renovate}")
        flow = RenovatorFlow(logger=logger)
        video_prompt = flow.run(args.renovate)
        print(f"\n--- Final Renovation Prompt for Veo 3 ---\n{video_prompt}")
        pass

    if args.sync:
        from bridge.mcp_client import SketchupBridge
        print("[Phase 1] Syncing with SketchUp...")
        bridge = SketchupBridge()
        model_info = bridge.get_model_info()
        logger.info(f"Model Info Synced: {model_info}")
        # In a real scenario, this would save to a temporary file or state
        print(f"Synced Model: {model_info.get('path', 'Unknown')}")
        pass

    if args.build_prompt:
        from prompt_engine.refiner import PromptRefiner
        print("[Phase 2] Synthesizing prompt components...")
        refiner = PromptRefiner(logger=logger)
        user_input = "Construction of a luxury modern house on an empty lot."
        final_prompt = refiner.refine_prompt(user_input)
        print(f"\n--- Final Synthesized Prompt ---\n{final_prompt}")
        pass

    if args.generate:
        from veo_provider.api_client import VeoClient
        print("[Phase 3] Generating video via Veo API...")
        veo = VeoClient()
        
        # In a real scenario, this would load the prompt and image from previous phases
        prompt = "Cinematic construction time-lapse of a luxury house villa emerging from an empty lot."
        image_path = "C:/gemini-proyek/video_time_lapse/pendekatan sketchup/start_frame.png"
        
        video_path = veo.generate_video(prompt, source_image_path=image_path)
        if video_path:
            logger.info(f"Video Generation Successful: {video_path}")
        pass

    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main()
