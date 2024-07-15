from dataclasses import dataclass

@dataclass
class SDProgress:
    progress: float
    eta_relative: float


class EndPoints:
    BASE = "http://127.0.0.1:7860"
    MODELS = BASE + "/sdapi/v1/sd-models"
    PROGRESS = BASE + "/internal/progress"
    OPTIONS = BASE + "/sdapi/v1/options"
    INTERRUPT = BASE + "/sdapi/v1/interrupt"
    
    TXT2IMG = BASE + "/sdapi/v1/txt2img"
    IMG2IMG = BASE + "/sdapi/v1/img2img"
