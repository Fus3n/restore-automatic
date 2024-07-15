from PySide6.QtWidgets import (
    QApplication, QMainWindow, 
    QGraphicsScene, QGraphicsView, QFrame, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QSplitter,
    QSlider, QComboBox, QRadioButton, QDoubleSpinBox, QCheckBox, QSpinBox, QLabel,
    QProgressBar, QFileDialog, QMessageBox
)

from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeyEvent, QPainter, QPixmap, QImage, QWheelEvent, QIcon
import requests

from PIL import Image

from typing import Literal

from restore_automatic.layer_list import LayerList
from restore_automatic import utils
import restore_automatic as rp
import os

from pprint import pprint

class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.zoom(1.0)

        self.pixmap_img = None
        self.pixmap_item = None

    def set_image(self, image):
        self.scene().clear()
        self.pixmap_img = QPixmap.fromImage(image)
        self.pixmap_item = self.scene().addPixmap(self.pixmap_img)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def save_image(self, path):
        if self.pixmap_img is None:
            return
        self.pixmap_img.save(path)

    def zoom(self, factor):
        self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            factor = 1.25
        else:
            factor = 1 / 1.25
        self.zoom(factor)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # on press home
        if event.key() == Qt.Key_Home:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

class SameLine(QFrame):
    def __init__(self, items: list):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

        lay = QHBoxLayout()
        for item in items:
            lay.addWidget(item)
        self.setLayout(lay)


class GenerationThread(QThread):

    GenTypes = Literal["img2img"] | Literal["txt2img"] | Literal["inpaint"]

    generated = Signal(list)
    failed = Signal(Exception)

    def __init__(self, gen_type: GenTypes, kwargs: dict):
        super().__init__(None)
        self.gen_type = gen_type
        self.kwargs = kwargs

    def run(self):
        try:
            if self.gen_type == "img2img":
                results = rp.sd_img2img(**self.kwargs)     
                self.generated.emit(results)
            elif self.gen_type == "txt2img":
                for item in ("base_img", "mask_path"):
                    if item in self.kwargs:
                        del self.kwargs[item]

                results = rp.sd_txt2img(**self.kwargs)
                self.generated.emit(results)
            print("finished")
        except Exception as e:
            self.failed.emit(e)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Restore Pro")
        self.resize(1280, 768)

        self.current_img_path = None
        self.image = None
        self._init_ui()

    def _init_ui(self):
        self.init_menu()

        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        # change handle color
        splitter.setStyleSheet("""
        QSplitter::handle {
            background-color: darkgray;
        }
        """)

        self.layers = LayerList(None)
        self.layers.item_pressed.connect(self.layer_item_pressed)
        self.layers.update_current.connect(self.layer_item_pressed)
        self.layers.setMinimumWidth(180)

        self.image_viewer = ImageViewer()
        # self.lay.addWidget(self.image_viewer)

        self.image = QImage(512, 512, QImage.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.white)

        self.image_viewer.set_image(self.image)
        self.layers.add_image("Layer", self.image)

        # Options
        content_frame = QFrame()
        # content_frame.setSize(250)
        contents = QVBoxLayout()
        contents.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_frame.setLayout(contents) 

        self.models_box = QComboBox()
        self.models_box.setMinimumHeight(30)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_models)

        contents.addWidget(SameLine([self.models_box, refresh_btn]))

        self.img2img_radio = QRadioButton("img2img")
        self.img2img_radio.setChecked(True)
        self.txt2img_radio = QRadioButton("text2img")
        self.inpaint_radio = QRadioButton("inpaint")

        contents.addWidget(SameLine([self.img2img_radio, self.txt2img_radio, self.inpaint_radio]))

        self.restore_faces_chk = QCheckBox("Restore Faces")
        self.restore_faces_chk.setChecked(False)
        contents.addWidget(self.restore_faces_chk)       

        self.presets_box = QComboBox()
        self.presets_box.setMinimumHeight(30)
        self.presets_box.addItems(["Normal", "Restoration", "Upscaling"]) 
        self.presets_box.activated.connect(self.set_preset)
        contents.addWidget(self.presets_box)

        self.prompt_input = self.get_input(placeholder="Prompt...")
        contents.addWidget(self.prompt_input)

        self.neg_prompt_input = self.get_input(placeholder="Negative Prompt...")
        contents.addWidget(self.neg_prompt_input)

        contents.addWidget(QLabel("Steps:"))
        self.steps_input = QSpinBox()
        self.steps_input.setValue(20)
        self.steps_input.setMaximum(150)
        contents.addWidget(self.steps_input)

        contents.addWidget(QLabel("CFG Scale:"))
        self.cfg_scale_input = QDoubleSpinBox()
        self.cfg_scale_input.setValue(7.5)
        self.cfg_scale_input.setMaximum(30)
        contents.addWidget(self.cfg_scale_input)

        self.width_input = QSpinBox()
        self.height_input = QSpinBox()
        self.width_input.setMaximum(6000)
        self.width_input.setValue(512)
        self.height_input.setMaximum(6000)
        self.height_input.setValue(512)

        reset_wh = QPushButton("Reset")
        reset_wh.clicked.connect(self.reset_wh)
        
        btnup1 = QPushButton(f"1.5X")
        btnup1.clicked.connect(lambda: self.__update_wh(btnup1))

        btndown1 = QPushButton(f"2X")
        btndown1.clicked.connect(lambda: self.__update_wh(btndown1))

        btnup4 = QPushButton(f"3X")
        btnup4.clicked.connect(lambda: self.__update_wh(btnup4))

        buttons = [reset_wh, btnup1, btndown1, btnup4]
        contents.addWidget(SameLine(buttons))

        wh_lay = QHBoxLayout()
        wh_lay.addWidget(QLabel("Width:"))
        wh_lay.addWidget(QLabel("Height:"))
        contents.addLayout(wh_lay)
        contents.addWidget(SameLine([self.width_input, self.height_input]))

        self.denoise_lbl = QLabel("Denoising Strength (0.3):")
        contents.addWidget(self.denoise_lbl)
        self.denoising_strength_input = QSlider(Qt.Horizontal)
        self.denoising_strength_input.setSingleStep(1)
        self.denoising_strength_input.setMinimum(0)
        self.denoising_strength_input.setMaximum(100)
        self.denoising_strength_input.setValue(30)
        # set from 0 to 1.0
        self.denoising_strength_input.valueChanged.connect(lambda v: self.denoise_lbl.setText(f"Denoising Strength ({v/100.0}):"))
        contents.addWidget(self.denoising_strength_input)

        contents.addWidget(QLabel("Seed:"))
        self.seed_input = QSpinBox()
        self.seed_input.setMinimum(-1)
        self.seed_input.setValue(-1)
        contents.addWidget(self.seed_input)

        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self.generate) 
        generate_btn.setMinimumHeight(35)   
        generate_btn.setStyleSheet("font-size: 18px;")
        contents.addWidget(generate_btn)    

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_generation) 
        stop_btn.setMinimumHeight(30)   
        stop_btn.setStyleSheet("font-size: 16px;")
        contents.addWidget(stop_btn)    

        self.prog = QProgressBar()
        self.prog.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prog.setRange(0, 0)
        self.prog.setVisible(False)
        contents.addWidget(self.prog)

        splitter.addWidget(self.layers)
        splitter.addWidget(self.image_viewer)
        splitter.addWidget(content_frame)
        self.setCentralWidget(splitter)

    def init_menu(self):
        menu = self.menuBar()
        menu.setNativeMenuBar(False)
        file = menu.addMenu("File")
        add_img = file.addAction("Add Image", self.add_image)
        add_img.setIcon(QIcon.fromTheme("document-open"))
        add_img.setShortcut("Ctrl+O")

        save_img = file.addAction("Save Image", self.save_image)
        save_img.setIcon(QIcon.fromTheme("document-save"))
        save_img.setShortcut("Ctrl+S")
        

        ex = file.addAction("Exit", self.close)
        ex.setIcon(QIcon.fromTheme("application-exit"))
    
    def layer_item_pressed(self, item):
        if item:
            self.image = item.image
            self.image_viewer.set_image(item.image)
            self.width_input.setValue(item.image.width())
            self.height_input.setValue(item.image.height())

    def __update_wh(self, value):
        value = float(value.text()[:-1])
        self.width_input.setValue(round(self.width_input.value() * value))
        self.height_input.setValue(round(self.height_input.value() * value))

    def update_width_height(self, width, height):
        self.width_input.setValue(width)
        self.height_input.setValue(height)

    def add_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            image = QImage(file_path)
            self.current_img_path = file_path
            self.image = image
            self.image_viewer.set_image(image)
            self.update_width_height(image.width(), image.height())
            self.layers.add_image(os.path.basename(file_path), image)

    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_viewer.save_image(file_path)

    def get_input(self, text="", placeholder=""):
        input_ = QTextEdit(text)
        input_.setPlaceholderText(placeholder)
        input_.setMinimumHeight(40)
        input_.setStyleSheet("""
        QTextEdit {
            border: 1px solid black; border-radius: 4px; font-size: 15px; }
        QTextEdit:focus {
            border-bottom: 1px solid lightblue;
        }
        """)
        return input_

    def set_preset(self, _):
        preset = self.presets_box.currentText()
        if preset == "Restoration" or "Upscaling":
            self.prompt_input.setText(utils.DEFAULT_RESTORE_PROMPT)
            self.neg_prompt_input.setText(utils.DEFAULT_RESTORE_NEGATIVE_PROMPT)
            self.img2img_radio.setChecked(True)
            self.txt2img_radio.setChecked(False)
            self.inpaint_radio.setChecked(False)
            self.denoising_strength_input.setValue(30 if preset == "Restoration" else 5)

    def reset_wh(self):
        self.update_width_height(self.image.width(), self.image.height())

    def generation_finished(self, images: list[Image.Image]):
        self.prog.setVisible(False)
        if images:
            self.image = images[0].toqimage()
            self.image_viewer.set_image(self.image)
            self.layers.add_image("generated", self.image)
            self.update_width_height(self.image.width(), self.image.height())
        else:
            print("Got 0 images")

    def gen_failed(self, err):
        self.prog.setVisible(False)
        print("Generation failed")
        print(err)

    def generate(self):
        if self.image is None:
            QMessageBox.critical(self, "Error", "No image selected")

        prompt = self.prompt_input.toPlainText()
        neg_prompt = self.neg_prompt_input.toPlainText()
        width = self.width_input.value()
        height = self.height_input.value()
        denoising_strength = self.denoising_strength_input.value()/100.0
        steps = self.steps_input.value()
        cfg_scale = self.cfg_scale_input.value()
        model = self.models_box.currentText()
        restore_faces = self.restore_faces_chk.isChecked()

        kwargs = {
            "base_img": Image.fromqimage(self.image),
            "prompt": prompt,
            "negative_prompt": neg_prompt,
            "model_name": model,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "denoising_strength": denoising_strength,
            "width": width,
            "height": height,
            "restore_faces": restore_faces,
            "seed": self.seed_input.value()
        }

        print("Starting with params:")
        pprint(kwargs)

        gen_type = "" 
        if self.txt2img_radio.isChecked():
            gen_type = "txt2img"
        elif self.img2img_radio.isChecked():
            gen_type = "img2img"
        elif self.inpaint_radio.isChecked():
            gen_type = "inpaint"
        else:
            gen_type = "txt2img"

        self.prog.setVisible(True)
        self.gen_thread = GenerationThread(gen_type, kwargs)
        self.gen_thread.generated.connect(self.generation_finished)
        self.gen_thread.failed.connect(self.gen_failed)
        self.gen_thread.start()

    def stop_generation(self):
        res = rp.sd_interrupt()
        print(res)
        self.prog.setVisible(False)

    def refresh_models(self):
        try:
            models = rp.sd_list_models()
            names = []
            for m in models:
                names.append(m["model_name"])

            self.models_box.addItems(names)
        except requests.exceptions.ConnectionError as e:
            QMessageBox.critical(self, "Error", "AUTOMATIC1111 webui is not running. Please start it first.")

def set_custom_fusion_theme(app, primary_color, secondary_color, text_color):
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(secondary_color))
    palette.setColor(QPalette.WindowText, QColor(text_color))
    palette.setColor(QPalette.Base, QColor(primary_color))
    palette.setColor(QPalette.AlternateBase, QColor(secondary_color))
    palette.setColor(QPalette.ToolTipBase, QColor(primary_color))
    palette.setColor(QPalette.ToolTipText, QColor(text_color))
    palette.setColor(QPalette.Text, QColor(text_color))
    palette.setColor(QPalette.Button, QColor(secondary_color))
    palette.setColor(QPalette.ButtonText, QColor(text_color))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(primary_color))
    
    app.setPalette(palette)
    app.setStyleSheet(f"""
        QToolTip {{ 
            color: {text_color}; 
            background-color: {primary_color}; 
            border: 1px solid {secondary_color}; 
        }}
    """)
if __name__ == "__main__":
    app = QApplication([])
    set_custom_fusion_theme(app, "#202020", "#1D1C1C", "#fff")
    window = MainWindow()
    window.show()

    app.exec()