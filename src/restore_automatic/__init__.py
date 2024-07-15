import requests
from pprint import pprint
from .types import EndPoints
from .utils import *
from PIL.Image import Image

DEFAULT_NEGATIVES = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"

def sd_inpaint(
        base_img_path: str | Image,
        mask_path: str | Image, 
        prompt: str, 
        model_name: str = None, 
        negative_prompt: str = DEFAULT_NEGATIVES,
        restore_faces: bool = False,
        steps=10, 
        cfg_scale=7,
        denoising_strength=7.5,
        width=512,
        height=512,
        batch_size=2,
        seed=-1,
        CLIP_stop_at_last_layers=2
    ):

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "mask": img2base64(mask_path) if type(mask_path) == str else pillowimg_to_base64(mask_path),
        "batch_size": batch_size,
        "mask_blur_x": 0,
        "mask_blur_y": 0,
        "mask_blur": 0,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "seed": seed,
        "denoising_strength": denoising_strength,
        "seed": seed,
        "restore_faces": restore_faces
    }

    if model_name is not None:
        payload["override_settings"] = {
            "sd_model_checkpoint": model_name,
            "CLIP_stop_at_last_layers": CLIP_stop_at_last_layers,
        }

    if type(base_img_path) == str:    
        payload["init_images"] = [img2base64(base_img_path)]
    else:
        payload["init_images"] = [pillowimg_to_base64(base_img_path)]

    response = requests.post(url=EndPoints.IMG2IMG, json=payload)
    jsn = response.json()
    pprint(jsn["parameters"])
    print(len(jsn["images"]))
    save_image(jsn["images"][0], "generated_img2img.png")

def sd_img2img(
        base_img: str | Image, 
        prompt: str, 
        negative_prompt: str = DEFAULT_NEGATIVES,
        model_name: str = None, 
        steps=10, 
        cfg_scale=7,
        denoising_strength=7.5,
        width=512,
        height=512,
        restore_faces: bool = False,
        batch_size=2,
        seed=-1,
        CLIP_stop_at_last_layers=2
    ) -> list[Image]:
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "batch_size": batch_size,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "seed": seed,
        "denoising_strength": denoising_strength,
        "restore_faces": restore_faces
    }

    if model_name is not None:
        payload["override_settings"] = {
            "sd_model_checkpoint": model_name,
            "CLIP_stop_at_last_layers": CLIP_stop_at_last_layers,
        }

    if type(base_img) == str:    
        payload["init_images"] = [img2base64(base_img)]
    else:
        payload["init_images"] = [pillowimg_to_base64(base_img)]

    response = requests.post(url=EndPoints.IMG2IMG, json=payload)
    jsn = response.json()
    images = [] 
    for im in jsn["images"]:
        images.append(base64_to_pillowimg(im))

    return images

def sd_txt2img(
        prompt: str,
        negative_prompt: str = DEFAULT_NEGATIVES,
        model_name: str = None, 
        steps=10, 
        cfg_scale=7,
        denoising_strength=7.5,
        width=512,
        height=512,
        batch_size=2,
        restore_faces: bool = False,
        seed=-1,
        CLIP_stop_at_last_layers=2
    ) -> list[Image]:

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "batch_size": batch_size,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "denoising_strength": denoising_strength,
        "seed": seed,
        "restore_faces": restore_faces
    }

    if model_name is not None:
        payload["override_settings"] = {
            "sd_model_checkpoint": model_name,
            "CLIP_stop_at_last_layers": CLIP_stop_at_last_layers,
            "show_progress_every_n_steps": int('1')
        }

    response = requests.post(url=EndPoints.TXT2IMG, json=payload)
    jsn = response.json()
    images = [] 
    for im in jsn["images"]:
        images.append(base64_to_pillowimg(im))

    return images

def set_model(model_name: str):
    modeldata = {
        "sd_model_checkpoint": model_name,
        "show_progress_every_n_steps": int('1')
    }

    paramheaders = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    paramresponse = requests.post(url=EndPoints.OPTIONS, headers=paramheaders, json=modeldata)
    if paramresponse.status_code != 200:
        raise Exception("Could not set model. Error: " + paramresponse.text)
    

def get_progress():
    payload = {
        # "id_task": "string",a
        # "id_live_preview": -1,
        # "live_preview": True,
        "skip_current_image": "false",
        "skip_current_text": "true"
    }
    response = requests.post(url=EndPoints.PROGRESS, json=payload)
    jsn = response.json()
    return jsn

def sd_list_models() -> list:
    model_resp = requests.get(EndPoints.MODELS)
    models = model_resp.json()
    return models

def sd_interrupt():
    resp = requests.post(url=EndPoints.INTERRUPT)
    return resp.status_code == 200