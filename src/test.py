from restore_automatic import sd_txt2img, get_progress, set_model
from threading import Thread
import time

def do_get_progress():
    while True:
        time.sleep(1)
        print(get_progress())

# set_model("AmazingArts-V2-merge3.safetensors")
# Thread(target=do_txt).start()
Thread(target=do_get_progress).start()