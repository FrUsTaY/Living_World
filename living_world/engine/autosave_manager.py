import os
from living_world.engine.event_bus import bus
from living_world.gui.tabs.settings_tab import load_settings

class AutosaveManager:
    """
    Менеджер автоматического сохранения симуляции.
    Периодически сохраняет снимок мира в файл saves/autosave.db
    согласно интервалу из настроек.
    """
    def __init__(self, simulation, saves_dir="saves"):
        self.simulation = simulation
        self.saves_dir = saves_dir
        if not os.path.exists(self.saves_dir):
            os.makedirs(self.saves_dir, exist_ok=True)
        self.last_saved_day = 0

    def check_and_autosave(self, current_day: int) -> bool:
        settings = load_settings()
        if not settings.get("autosave_enabled", True):
            return False

        interval_days = max(1, settings.get("autosave_interval_days", 5))
        filename = settings.get("autosave_filename", "autosave.db").strip() or "autosave.db"

        if current_day > 0 and (current_day % interval_days == 0) and (current_day != self.last_saved_day):
            self.last_saved_day = current_day
            return self.perform_autosave(filename)
        return False

    def perform_autosave(self, filename: str = "autosave.db") -> bool:
        target_path = os.path.join(self.saves_dir, filename)
        tmp_path = target_path + ".tmp"
        try:
            self.simulation.save_to_file(tmp_path)
            if os.path.exists(target_path):
                os.replace(tmp_path, target_path)
            else:
                os.rename(tmp_path, target_path)
            bus.publish("log_event", f"💾 Автосохранение мира успешно выполнено ({filename}).")
            return True
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            bus.publish("log_event", f"⚠ Ошибка автосохранения: {e}")
            return False
