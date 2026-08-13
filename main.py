import sys
from PySide6.QtWidgets import QApplication
from living_world.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    # По умолчанию создаем новый мир при запуске
    window.new_world()

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
