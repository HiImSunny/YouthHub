import logging
import subprocess

logger = logging.getLogger(__name__)

def get_hardware_info() -> dict:
    """Return dict with ram_gb and vram_gb"""
    info = {'vram_gb': 0, 'ram_gb': 8} # Default assume 8GB system RAM
    try:
        # Get VRAM
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            text=True,
            stderr=subprocess.STDOUT
        ).strip().split('\n')
        max_vram = 0
        for line in output:
            try:
                max_vram = max(max_vram, int(line))
            except ValueError:
                pass
        info['vram_gb'] = max_vram / 1024.0
    except Exception:
        pass
    return info

def detect_best_model() -> str:
    info = get_hardware_info()
    vram = info.get('vram_gb', 0)
    ram = info.get('ram_gb', 8)  # Default 8GB if cannot detect
    
    # 1. Highest tier: sailor2:20b (RAM 24GB or VRAM 16GB+)
    if vram >= 14 or ram >= 24:
        return 'sailor2:20b'
    
    # 2. High tier: qwen3:8b or sailor2:8b needs 8GB VRAM to not crash. If vram is ~6-7GB it might, but let's be safe.
    elif vram >= 5.5:
        return 'sailor2:8b'
    
    # 3. Mid tier: qwen3:4b (requires ~3.5GB VRAM or 6GB RAM)
    elif vram >= 3.5:
        return 'qwen3:4b'
        
    # 4. Low-mid tier: qwen2.5:3b (requires ~2.5GB VRAM)
    elif vram >= 2.5:
        return 'qwen2.5:3b'
        
    # 5. Low tier (RAM only / VRAM < 2.5GB): sailor2:1b
    else:
        return 'sailor2:1b'
