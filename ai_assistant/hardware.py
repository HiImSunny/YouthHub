import logging
import subprocess

logger = logging.getLogger(__name__)

def detect_best_model() -> str:
    """
    Detect hardware VRAM and return the recommended Qwen 2.5 model.
    - >= 4096MB VRAM: qwen2.5:3b-instruct
    - < 4096MB VRAM or No GPU: qwen2.5:1.5b-instruct
    """
    try:
        # Get total memory mapping from all GPUs
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            text=True,
            stderr=subprocess.STDOUT
        ).strip().split('\n')
        
        # We check if *any* GPU has 4GB+
        has_large_vram = False
        max_vram = 0
        for line in output:
            try:
                vram = int(line)
                max_vram = max(max_vram, vram)
                if vram >= 4096:
                    has_large_vram = True
            except ValueError:
                continue

        if has_large_vram:
            logger.info(f"Detected NVIDIA GPU with {max_vram}MB VRAM. Selecting 'qwen2.5:3b-instruct'.")
            return "qwen2.5:3b-instruct"
        else:
            logger.info(f"Detected NVIDIA GPU with {max_vram}MB VRAM. Fallback to 'qwen2.5:1.5b-instruct'.")
            return "qwen2.5:1.5b-instruct"

    except Exception as e:
        logger.info(f"No suitable NVIDIA GPU found or driver error ({e}). Fallback to 'qwen2.5:1.5b-instruct'.")
        return "qwen2.5:1.5b-instruct"
