import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from living_world.gui.main_window import MainWindow
from living_world.population.generation import generate_initial_world

def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    # If new world, initialize with starting population
    if not window.sim.npcs:
        generate_initial_world(window.sim.city, window.sim, 25)
        for tab in [
            window.world_tab,
            window.pop_tab,
            window.fam_tab,
            window.city_tab,
            window.stats_tab,
            window.history_tab,
            window.events_tab,
            window.settings_tab
        ]:
            if hasattr(tab, "update_data"):
                tab.update_data()
        window.update_log()
        window.lbl_time.setText(window.sim.time.format_time())

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
