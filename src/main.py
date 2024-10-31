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
from PySide6.QtWidgets import QWidget, QCheckBox
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

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        form = QFormLayout()

        self.radius_line = FloatLineEdit()
        self.radius_line.setText(str(50))
        self.move_feed = FloatLineEdit()
        self.move_feed.setText(str(5000))
        self.flipflop = QCheckBox()

        form.addRow("Radius (mm)", self.radius_line)
        form.addRow("Move Feed (mm/min)", self.move_feed)
        form.addRow("Flipflop Direction", self.flipflop)

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

        self.load_settings()

    def move_command(self):
        print("Moving")

        feed = self.move_feed.text()
        radius = float(
            self.radius_line.text()
        )  # Convert radius to float for calculations
        clockwise_rotation = self.clockwise_radio.isChecked()
        half_rotation = self.half.isChecked()

        # Determine rotation degrees based on user selection
        rot = 180 if half_rotation else 90
        direction = "clockwise" if clockwise_rotation else "counterclockwise"

        # Set feed rate
        gcode_cmd(f"G1 F{feed}")

        # Define initial positions for each direction around (X0, Y0)
        start_pos = {
            "east": (radius, 0),
            "north": (0, radius),
            "west": (-radius, 0),
            "south": (0, -radius),
        }

        # Get the starting position based on self.pos
        if self.pos in start_pos:
            start_x, start_y = start_pos[self.pos]
            gcode_cmd(f"G1 X{start_x} Y{start_y}")  # Move to the starting position

        # Determine the target endpoint and arc center offset (I, J)
        end_x, end_y, i_offset, j_offset = 0, 0, 0, 0  # Initialize

        # Calculate end positions and I/J offsets based on the initial direction and rotation
        if self.pos == "east":
            if direction == "clockwise":
                if rot == 90:
                    end_x, end_y = 0, -radius  # Move to south
                    i_offset, j_offset = -radius, 0
                elif rot == 180:
                    end_x, end_y = -radius, 0  # Move to west
                    i_offset, j_offset = -radius, 0
            else:  # Counterclockwise
                if rot == 90:
                    end_x, end_y = 0, radius  # Move to north
                    i_offset, j_offset = -radius, 0
                elif rot == 180:
                    end_x, end_y = -radius, 0  # Move to west
                    i_offset, j_offset = -radius, 0

        elif self.pos == "north":
            if direction == "clockwise":
                if rot == 90:
                    end_x, end_y = radius, 0  # Move to east
                    i_offset, j_offset = 0, -radius
                elif rot == 180:
                    end_x, end_y = 0, -radius  # Move to south
                    i_offset, j_offset = 0, -radius
            else:  # Counterclockwise
                if rot == 90:
                    end_x, end_y = -radius, 0  # Move to west
                    i_offset, j_offset = 0, -radius
                elif rot == 180:
                    end_x, end_y = 0, -radius  # Move to south
                    i_offset, j_offset = 0, -radius

        elif self.pos == "west":
            if direction == "clockwise":
                if rot == 90:
                    end_x, end_y = 0, radius  # Move to north
                    i_offset, j_offset = radius, 0
                elif rot == 180:
                    end_x, end_y = radius, 0  # Move to east
                    i_offset, j_offset = radius, 0
            else:  # Counterclockwise
                if rot == 90:
                    end_x, end_y = 0, -radius  # Move to south
                    i_offset, j_offset = radius, 0
                elif rot == 180:
                    end_x, end_y = radius, 0  # Move to east
                    i_offset, j_offset = radius, 0

        elif self.pos == "south":
            if direction == "clockwise":
                if rot == 90:
                    end_x, end_y = -radius, 0  # Move to west
                    i_offset, j_offset = 0, radius
                elif rot == 180:
                    end_x, end_y = 0, radius  # Move to north
                    i_offset, j_offset = 0, radius
            else:  # Counterclockwise
                if rot == 90:
                    end_x, end_y = radius, 0  # Move to east
                    i_offset, j_offset = 0, radius
                elif rot == 180:
                    end_x, end_y = 0, radius  # Move to north
                    i_offset, j_offset = 0, radius

        # Execute the G-code arc command based on rotation direction
        if direction == "clockwise":
            gcode_cmd(f"G2 X{end_x} Y{end_y} I{i_offset} J{j_offset}")
        else:
            gcode_cmd(f"G3 X{end_x} Y{end_y} I{i_offset} J{j_offset}")

        # Update current position
        self.pos = get_final_direction(self.pos, rot, direction)
        print(f"Moved to position: {self.pos}")

        if self.flipflop.isChecked():
            if self.clockwise_radio.isChecked():
                self.counterclockwise_radio.setChecked(True)
            else:
                self.clockwise_radio.setChecked(True)

    def load_settings(self) -> None:
        settings = QSettings("spindle-tramming-tool", "SpindleTrammingTool")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

        self.clockwise_radio.setChecked(
            settings.value("clockwise_radio", False, type=bool)
        )
        self.counterclockwise_radio.setChecked(
            settings.value("counterclockwise_radio", False, type=bool)
        )

        self.quarter.setChecked(settings.value("quarter", False, type=bool))
        self.half.setChecked(settings.value("half", False, type=bool))
        self.flipflop.setChecked(settings.value("flipflop", False, type=bool))

        self.radius_line.setText(
            settings.value("radius", "50")
        )  # Default to 50 if not saved
        self.move_feed.setText(
            settings.value("feed", "1000")
        )  # Default to 50 if not saved

    def closeEvent(self, event):
        self.save_settings()  # Save settings when the tool closes
        super().closeEvent(event)

    def save_settings(self):
        settings = QSettings("spindle-tramming-tool", "SpindleTrammingTool")

        # Save radio button states
        settings.setValue("clockwise_radio", self.clockwise_radio.isChecked())
        settings.setValue(
            "counterclockwise_radio", self.counterclockwise_radio.isChecked()
        )
        settings.setValue("quarter", self.quarter.isChecked())
        settings.setValue("half", self.half.isChecked())
        settings.setValue("flipflop", self.flipflop.isChecked())

        # Save radius
        settings.setValue("radius", self.radius_line.text())
        settings.setValue("feed", self.move_feed.text())


def start() -> None:
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(additional_qss="QToolTip {color: black;}")

    window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    start()
