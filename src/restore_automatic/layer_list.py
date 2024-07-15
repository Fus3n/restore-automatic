from PySide6.QtWidgets import QListWidget, QWidget, QListWidgetItem, QHBoxLayout, QLabel, QAbstractItemView, QMenuBar, QMenu
from PySide6.QtCore import QItemSelection, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPixmap, QImage, QIcon

class LayerItem(QWidget):

    clicked = Signal(type)

    def __init__(self, name, image: QImage):
        super().__init__(None)
        self.name = name
        self.image = image
        self.item: QListWidgetItem = None

        self.lay = QHBoxLayout()
        self.lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.img_lbl = QLabel()
        img = image.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_lbl.setPixmap(QPixmap.fromImage(img))
        self.lay.addWidget(self.img_lbl)

        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet("font-size: 16px;")
        self.lay.addWidget(self.name_lbl)

        self.setLayout(self.lay)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)  

class LayerList(QListWidget):

    item_pressed = Signal(LayerItem)
    update_current = Signal(LayerItem)

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.setItemAlignment(Qt.AlignmentFlag.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu_requested)

    def add_image(self, name: str, image: QImage):
        widget = LayerItem(name, image)
        widget.clicked.connect(self.item_clicked)
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEnabled)
        item.setSizeHint(widget.sizeHint())
        widget.item = item
        self.insertItem(0, item)
        self.setItemWidget(item, widget)
        self.setCurrentItem(item)

    def item_clicked(self, item: LayerItem):
        self.setCurrentItem(item.item)       
        self.item_pressed.emit(item)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:
            self.delete_layer()

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        return super().selectionChanged(selected, deselected)

    def delete_layer(self):
        # check if selected
        if not self.selectedItems():
            return

        # delete selected
        for item in self.selectedItems():
            self.takeItem(self.row(item))

        first_item = self.item(0)
        if first_item:
            widget = self.itemWidget(first_item)
            self.setCurrentItem(widget.item)
            self.update_current.emit(widget)

    def on_context_menu_requested(self, pos):
        item = self.itemAt(pos)
        
        if item is not None:
            context_menu = QMenu(self)
            
            add_to_ps = context_menu.addAction("Add to Photoshop")
            add_to_ps.setIcon(QIcon.fromTheme("document-open"))

            
            chosen_action = context_menu.exec(self.viewport().mapToGlobal(pos))
            
            # # Handle the chosen action
            # if chosen_action == add_to_ps:
            #     print(f"Add to Photoshop")
            # elif chosen_action == action2:
            #     print(f"")
            # elif chosen_action == action3: