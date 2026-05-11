import os
import sys
import argparse
import json
from datetime import datetime
from core.logger import ProductionLogger

def main():
    parser = argparse.ArgumentParser(description="Veo Content Factory")
    parser.add_argument("--niche", type=str, default="construction_timelapse", help="Niche slug")
    parser.add_argument("--input", type=str, required=True, help="User input / idea")
    parser.add_argument("--image", type=str, help="Path to reference image (for image-to-video)")
    parser.add_argument("--generate", action="store_true", help="Generate video after prompt refinement")
    parser.add_argument("--output", type=str, help="Output path for video")
    parser.add_argument("--mode", type=str, choices=["lite", "fast", "standard"], help="Veo tier override")
    parser.add_argument("--save", action="store_true", help="Save prompt to docs/prompts")

    args = parser.parse_args()

    logger = ProductionLogger()
    logger.info(f"Veo Content Factory — niche: {args.niche}")

    from prompt_engine.refiner import PromptRefiner
    refiner = PromptRefiner(logger=logger)

    print(f"\n{'='*50}")
    print(f"REFINING PROMPT")
    print(f"Niche      : {args.niche}")
    print(f"Input      : {args.input[:80]}...")
    print(f"Reference  : {args.image or 'none (text-to-video)'}")
    print(f"{'='*50}\n")

    result = refiner.refine_prompt(
        user_input=args.input,
        niche_slug=args.niche,
        image_path=args.image,
    )

    print(f"\n{'='*50}")
    print(f"PROMPT RESULT")
    print(f"Score      : {result.get('score', 'N/A')}/10")
    print(f"{'='*50}")
    print(f"\nPOSITIVE PROMPT:")
    print(result.get("positive", ""))
    print(f"\nNEGATIVE PROMPT:")
    print(result.get("negative", "none"))
    print(f"\n{'='*50}")

    if args.save:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = os.path.join("..", "docs", "prompts")
        os.makedirs(outdir, exist_ok=True)
        outpath = os.path.join(outdir, f"prompt_{args.niche}_{ts}.json")
        with open(outpath, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nPrompt saved: {outpath}")

    if args.generate:
        from veo_provider.api_client import VeoClient
        print(f"\n{'='*50}")
        print(f"GENERATING VIDEO")
        print(f"{'='*50}")

        veo = VeoClient()
        if args.mode:
            veo.config["mode"] = args.mode
            mode = args.mode
            veo.model_id = veo.config["model_ids"][mode]

        cost = veo.estimate_cost()
        print(f"Estimated cost: ${cost}")
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Skipped.")
            return

        video_path = veo.generate_video(
            prompt=result,
            source_image_path=args.image,
            output_filename=args.output,
        )

        if video_path:
            logger.info(f"Video generated: {video_path}")
            print(f"\n✅ VIDEO READY: {video_path}")
        else:
            print(f"\n❌ VIDEO GENERATION FAILED")
            sys.exit(1)

if __name__ == "__main__":
    main()
