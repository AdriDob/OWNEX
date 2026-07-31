# ComfyUI + FLUX Installation Guide

> **Setup guide for OWNEX OMEGA brand image generation pipeline**
> *ComfyUI with FLUX Dev/Schnell for premium brand asset generation*

---

## System Requirements

### Hardware
- **GPU:** NVIDIA GPU with 8GB+ VRAM (12GB+ recommended)
- **RAM:** 16GB (32GB recommended)
- **Storage:** 15-65GB free disk space per model
- **OS:** Windows 10/11, Linux, macOS (Linux recommended)

### Software
- **Python:** 3.10 (recommended)
- **CUDA:** 11.8+ (12.1+ recommended)
- **Git:** For cloning repositories
- **Virtual Environment:** python3-venv or conda

---

## Installation Steps

### Step 1: Install ComfyUI

#### Linux/macOS
```bash
# Clone ComfyUI repository
cd /home/adrie/projects/Rastro
git clone https://github.com/comfyanonymous/ComfyUI.git .ai/brand/comfyui

# Create virtual environment
cd .ai/brand/comfyui
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

#### Windows
```powershell
# Clone ComfyUI repository
cd C:\projects\Rastro
git clone https://github.com/comfyanonymous/ComfyUI.git .ai\brand\comfyui

# Create virtual environment
cd .ai\brand\comfyui
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### Step 2: Install ComfyUI Manager

```bash
cd .ai/brand/comfyui/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

### Step 3: Download FLUX Models

#### Option A: FLUX.1 Schnell (Recommended - Fast, Apache 2.0 Commercial)
```bash
cd .ai/brand/comfyui/models/checkpoints
wget https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors
```

#### Option B: FLUX.1 Dev (Highest Quality, Non-Commercial)
```bash
cd .ai/brand/comfyui/models/checkpoints
# Requires HuggingFace account and license acceptance
wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors
```

#### Option C: FLUX.2 Klein 4B (Fast, Commercial, Latest)
```bash
cd .ai/brand/comfyui/models/checkpoints
wget https://huggingface.co/black-forest-labs/FLUX.2-klein/resolve/main/flux2-klein.safetensors
```

### Step 4: Download Required Text Encoders

```bash
# CLIP encoder
cd .ai/brand/comfyui/models/clip
wget https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors

# T5 encoder (for Dev models)
cd .ai/brand/comfyui/models/clip
wget https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors

# VAE
cd .ai/brand/comfyui/models/vae
wget https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/ae.safetensors
```

### Step 5: Install FLUX Custom Nodes

```bash
cd .ai/brand/comfyui
# Start ComfyUI once to initialize
python main.py

# Open browser to http://127.0.0.1:8188
# Go to Manager tab
# Install: ComfyUI-Flux, ComfyUI-Essentials
```

---

## Launching ComfyUI

### Development Mode
```bash
cd .ai/brand/comfyui
source venv/bin/activate  # Linux/macOS
# or venv\Scripts\activate  # Windows
python main.py --listen 0.0.0.0 --port 8188
```

### Production Mode
```bash
cd .ai/brand/comfyui
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --high-vram
```

---

## Workflow Configuration

### OWNEX Brand Workflows

Workflows are stored in `.ai/brand/generation_pipeline/workflows/`

#### Logo Generation Workflow
- File: `logo_generation.json`
- Model: FLUX.1 Schnell (fast iteration)
- Resolution: 1024x1024
- CFG Scale: 1.0
- Steps: 4

#### Hero Banner Workflow
- File: `hero_banner.json`
- Model: FLUX.1 Dev (highest quality)
- Resolution: 1920x1080
- CFG Scale: 1.0
- Steps: 20-28

#### Icon Generation Workflow
- File: `icon_generation.json`
- Model: FLUX.1 Schnell (fast iteration)
- Resolution: 512x512
- CFG Scale: 1.0
- Steps: 4

---

## Prompt Integration

### Prompt Library Integration
Prompts from `PROMPT_LIBRARY.md` are integrated into ComfyUI workflows:

```python
# Example prompt integration
from .ai.brand.PROMPT_LIBRARY import LOGO_PROMPTS

def generate_logo_concept(concept_number):
    prompt = LOGO_PROMPTS[concept_number]
    # Apply to ComfyUI workflow
    workflow = load_workflow('logo_generation.json')
    workflow['prompt'] = prompt
    return workflow
```

---

## Automation Script

### Batch Generation Script

```python
#!/usr/bin/env python3
"""
OWNEX Brand Asset Generation Script
Automates batch generation of brand concepts using ComfyUI + FLUX
"""

import json
import requests
from pathlib import Path

class BrandAssetGenerator:
    def __init__(self, comfyui_url="http://127.0.0.1:8188"):
        self.comfyui_url = comfyui_url
        self.workflows_dir = Path(".ai/brand/generation_pipeline/workflows")
        self.output_dir = Path(".ai/brand/generation_pipeline/output")
        self.prompts_dir = Path(".ai/brand/generation_pipeline/prompts")
        
    def load_workflow(self, workflow_name):
        """Load ComfyUI workflow JSON"""
        workflow_path = self.workflows_dir / f"{workflow_name}.json"
        with open(workflow_path) as f:
            return json.load(f)
    
    def load_prompt(self, prompt_name):
        """Load prompt from prompt library"""
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        with open(prompt_path) as f:
            return f.read()
    
    def generate_image(self, workflow, prompt):
        """Generate image using ComfyUI API"""
        # Update workflow with prompt
        workflow["prompt"]["KSampler"]["seed"] = random.randint(0, 1000000)
        workflow["prompt"]["CLIP Text Encode"]["text"] = prompt
        
        # Submit to ComfyUI
        response = requests.post(
            f"{self.comfyui_url}/prompt",
            json={"prompt": workflow}
        )
        
        return response.json()
    
    def batch_generate(self, category, concepts):
        """Generate multiple concepts for a category"""
        workflow = self.load_workflow(category)
        results = []
        
        for concept in concepts:
            prompt = self.load_prompt(f"{category}_{concept}")
            result = self.generate_image(workflow, prompt)
            results.append(result)
        
        return results

if __name__ == "__main__":
    generator = BrandAssetGenerator()
    
    # Example: Generate 10 logo concepts
    logo_concepts = [f"logo_{i}" for i in range(1, 11)]
    results = generator.batch_generate("logo_generation", logo_concepts)
    
    print(f"Generated {len(results)} logo concepts")
```

---

## Quality Control

### Automated Quality Checks

```python
def check_generated_image(image_path):
    """Check generated image against quality standards"""
    # Check resolution
    img = Image.open(image_path)
    assert img.width >= 1024, "Image too small"
    
    # Check file size
    assert image_path.stat().st_size < 10_000_000, "File too large"
    
    # Check color space
    assert img.mode == "RGB", "Wrong color space"
    
    return True
```

---

## Troubleshooting

### Common Issues

#### Out of Memory (OOM)
- Reduce batch size
- Use FP8 quantized models
- Reduce resolution
- Close other applications

#### Slow Generation
- Use FLUX Schnell instead of Dev
- Reduce steps
- Use GPU with more VRAM
- Enable --high-vram flag

#### Poor Quality
- Increase steps (for Dev models)
- Adjust CFG scale
- Refine prompts
- Use higher resolution

#### Model Not Found
- Check model directory structure
- Verify model download completed
- Check file permissions
- Restart ComfyUI

---

## Performance Optimization

### GPU Optimization
```bash
# Enable high VRAM mode
python main.py --high-vram

# Enable FP16 (if supported)
python main.py --fp16-vae

# Enable attention optimization
python main.py --attention-pytorch
```

### CPU Optimization
```bash
# Limit CPU threads
export OMP_NUM_THREADS=4

# Enable optimizations
python main.py --force-fp16
```

---

## Security Considerations

### API Security
- Run ComfyUI locally only (not exposed to internet)
- Use firewall to restrict access
- No authentication required for local use
- Never share ComfyUI instance publicly

### Model Security
- Download models from official sources only
- Verify model checksums
- Keep models updated
- Respect model licenses

---

## Maintenance

### Regular Updates
```bash
cd .ai/brand/comfyui
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Model Updates
- Check HuggingFace for model updates
- Download new versions when available
- Test new versions before production use
- Archive old versions

### Cleanup
```bash
# Clear cache
rm -rf .ai/brand/comfyui/models/vae_cache

# Clear output
rm -rf .ai/brand/generation_pipeline/output/*
```

---

## Integration with OWNEX

### OWNEX Integration Points
- **Brand Department:** Uses for asset generation
- **Documentation:** Auto-generates diagrams
- **Marketing:** Creates promotional materials
- **Website:** Generates hero images
- **Mobile:** Generates app icons and screenshots

### Automation Pipeline
1. Design request submitted
2. Prompt selected from library
3. Workflow loaded
4. Images generated
5. Quality checked
6. Assets approved
7. Integrated into codebase

---

**ComfyUI Installation Guide v1.0**
*Last updated: 2026-07-31*
*Version: 7.0.0*