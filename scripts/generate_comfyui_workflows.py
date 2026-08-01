"""ComfyUI Workflow Generator for OWNEX Video Trailer.

Creates workflow JSON files for ComfyUI to generate video scenes.
Note: Video generation requires:
- GPU with 12GB+ VRAM recommended
- Stable Video Diffusion / Hunyuan Video / Wan models
- Significant render time (hours for 95 seconds)
- Manual ComfyUI setup and model downloads
"""

from pathlib import Path
import json

WORKFLOWS_DIR = Path("assets/video_generation/workflows")

# Basic ComfyUI workflow template for video generation
# This is a simplified template - actual workflows depend on specific models
WORKFLOW_TEMPLATE = {
    "1": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 123456789,
            "steps": 20,
            "cfg": 7,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        }
    },
    "2": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "stable_video_diffusion.safetensors"
        }
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "positive prompt",
            "clip": ["2", 1]
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "negative prompt",
            "clip": ["2", 1]
        }
    },
    "5": {
        "class_type": "EmptyLatentVideo",
        "inputs": {
            "width": 1920,
            "height": 1080,
            "length": 24,
            "batch_size": 1
        }
    },
    "6": {
        "class_type": "VAEDecodeVideo",
        "inputs": {
            "samples": ["1", 0],
            "vae": ["2", 2]
        }
    },
    "7": {
        "class_type": "SaveLatent",
        "inputs": {
            "samples": ["5", 0]
        }
    }
}

# Load scene prompts
prompts_file = Path("assets/video_generation/prompts/scene_prompts.json")
with open(prompts_file, "r") as f:
    scene_prompts = json.load(f)

# Generate workflow for each scene
for scene_name, scene_data in scene_prompts.items():
    workflow = WORKFLOW_TEMPLATE.copy()
    
    # Customize workflow for scene
    workflow["3"]["inputs"]["text"] = scene_data["visual"]
    workflow["4"]["inputs"]["text"] = "robots, humanoids, digital brains, AI clichés, excessive neon, clutter, low quality, blurry, distorted"
    
    # Adjust video length based on duration
    duration_str = scene_data["duration"]
    duration_num = int(duration_str.split()[0])  # Extract number from "8 seconds"
    frames = duration_num * 30  # 30 fps
    workflow["5"]["inputs"]["length"] = frames
    
    # Save workflow
    workflow_file = WORKFLOWS_DIR / f"{scene_name}_workflow.json"
    with open(workflow_file, "w") as f:
        json.dump(workflow, f, indent=2)
    
    print(f"✓ Workflow generated: {workflow_file}")

# Generate boot sequence workflow
boot_prompt_file = Path("assets/video_generation/prompts/boot_sequence_prompt.json")
with open(boot_prompt_file, "r") as f:
    boot_prompt = json.load(f)

boot_workflow = WORKFLOW_TEMPLATE.copy()
boot_workflow["3"]["inputs"]["text"] = boot_prompt["visual"]
boot_workflow["4"]["inputs"]["text"] = "robots, humanoids, digital brains, AI clichés, excessive neon, clutter, low quality"
boot_duration_str = boot_prompt["duration"]
boot_duration_num = int(boot_duration_str.split()[0])
boot_workflow["5"]["inputs"]["length"] = boot_duration_num * 30

boot_workflow_file = WORKFLOWS_DIR / "boot_sequence_workflow.json"
with open(boot_workflow_file, "w") as f:
    json.dump(boot_workflow, f, indent=2)

print(f"✓ Boot sequence workflow generated: {boot_workflow_file}")

print(f"\nAll workflows generated in: {WORKFLOWS_DIR}")
print(f"  - {len(scene_prompts)} scene workflows")
print(f"  - 1 boot sequence workflow")
print(f"\n⚠️  Note: These are template workflows.")
print(f"    Actual video generation requires:")
print(f"    - GPU with 12GB+ VRAM")
print(f"    - Stable Video Diffusion / Hunyuan Video / Wan models")
print(f"    - Manual ComfyUI setup")
print(f"    - Model downloads (10GB+)")
print(f"    - Significant render time (hours)")
