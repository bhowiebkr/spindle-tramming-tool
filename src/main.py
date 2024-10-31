import qdarktheme


from PySide6.QtCore import QSettings
from PySide6.QtCore import Qt
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QFormLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QSlider
from PySide6.QtWidgets import QSplitter
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QRadioButton
from PySide6.QtWidgets import QButtonGroup

import sys
import time
import linuxcnc

from src.custom_widgets import FloatLineEdit
from enum import Enum


class Pos(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4


class Rot(Enum):
    FULL = 1
    HALF = 2
    QUARTER = 3


def get_final_direction(
    starting_direction: str, rotation_degrees: int, rotation_direction: str
) -> str:
    # Define the possible directions in clockwise order
    directions = ["north", "east", "south", "west"]

    # Convert starting direction to lowercase to avoid case-sensitivity issues
    starting_direction = starting_direction.lower()

    # Check inputs for validity
    if starting_direction not in directions:
        raise ValueError(
            "Starting direction must be 'north', 'south', 'east', or 'west'."
        )
    if rotation_degrees not in [90, 180]:
        raise ValueError("Rotation must be either 90 or 180 degrees.")
    if rotation_direction.lower() not in ["clockwise", "counterclockwise"]:
        raise ValueError(
            "Rotation direction must be 'clockwise' or 'counterclockwise'."
        )

    # Find the index of the starting direction
    start_index = directions.index(starting_direction)

    # Calculate the steps to move based on rotation degree and direction
    steps = rotation_degrees // 90  # 90 degrees = 1 step, 180 degrees = 2 steps
    if rotation_direction.lower() == "counterclockwise":
        steps = -steps

    # Determine the final index by rotating within the list
    final_index = (start_index + steps) % len(directions)
    return directions[final_index]


def gcode_cmd(gcode):
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    cmd.mode(linuxcnc.MODE_MDI)
    cmd.mdi(gcode)
    cmd.wait_complete()  # wait until mode switch executed

    def ready():
        stat.poll()
        return (
            not stat.estop
            and stat.enabled
            and (stat.homed.count(1) == stat.joints)
            and (stat.interp_state == linuxcnc.INTERP_IDLE)
        )

    while not ready():
        continue


# Define the main window
class MainWindow(QMainWindow):  # type: ignore
    def __init__(self) -> None:
        super().__init__()

        self.pos = "east"
        self.setWindowTitle("Spindle Tramming Tool")

        self.load_settings()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        form = QFormLayout()

        self.radius_line = FloatLineEdit()
        self.radius_line.setText(str(50))
        self.move_feed = FloatLineEdit()
        self.move_feed.setText(str(5000))

        form.addRow("Radius (mm)", self.radius_line)
        form.addRow("Move Feed (mm/min)", self.move_feed)

        direction_layout = QHBoxLayout()

        dir_group = QButtonGroup(self)
        self.counterclockwise_radio = QRadioButton("Counterclockwise")
        self.clockwise_radio = QRadioButton("Clockwise")
        dir_group.addButton(self.counterclockwise_radio)
        dir_group.addButton(self.clockwise_radio)
        self.clockwise_radio.setChecked(True)
        direction_layout.addWidget(self.clockwise_radio)
        direction_layout.addWidget(self.counterclockwise_radio)

        step_group = QButtonGroup(self)
        step_layout = QHBoxLayout()
        self.quarter = QRadioButton("90°")
        self.half = QRadioButton("180°")
        step_group.addButton(self.quarter)
        step_group.addButton(self.half)
        self.half.setChecked(True)
        step_layout.addWidget(self.quarter)
        step_layout.addWidget(self.half)

        move_btn = QPushButton("Move")
        move_btn.setFixedHeight(50)

        main_layout.addLayout(form)
        main_layout.addLayout(direction_layout)
        main_layout.addLayout(step_layout)

        main_layout.addWidget(move_btn)

        move_btn.clicked.connect(self.move_command)

    def move_command(self):
        print("Moving")

        feed = self.move_feed.text()
        radius = self.radius_line.text()
        clockwise_rotation = self.clockwise_radio.isChecked()
        half_rotation = self.half.isChecked()

        if half_rotation:
            rot = 180
        else:
            rot = 90

        if clockwise_rotation:
            direction = "clockwise"
        else:
            direction = "counterclockwise"

        self.pos = get_final_direction(self.pos, rot, direction)

        gcode_cmd(f"G1 F{feed}")

        X = 0
        Y = 0

        if self.pos == "east":
            X = radius
            Y = 0
        elif self.pos == "west":
            X = -radius
            Y = 0

        elif self.pos == "north":
            X = 0
            Y = radius
        elif self.pos == "south":
            X = 0
            Y = -radius

        next_pos = get_final_direction(self.pos, rot, direction)

        if direction == "clockwise" and rot == 180:

            gcode_cmd(f"G1 X {radius}")

            gcode_cmd(f"G03 I-{radius} J0")

    def load_settings(self) -> None:
        settings = QSettings("spindle-tramming-tool", "SpindleTrammingTool")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings = QSettings("spindle-tramming-tool", "SpindleTrammingTool")
        self.settings.setValue("geometry", self.saveGeometry())

        # Cleanup the threads
        # self.core.workerThread.quit()
        # self.core.workerThread.wait()

        # Close the ballbar thread

        self.deleteLater()
        super().closeEvent(event)


def start() -> None:
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(additional_qss="QToolTip {color: black;}")

    window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start()
