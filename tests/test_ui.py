"""Проверки заставки, клавиатуры и тайлов на реальном Canvas."""

from types import SimpleNamespace
import unittest

import config as cfg
from main import prepare_tk
from models import Explosion
from view import App


class InterfaceTests(unittest.TestCase):
    """Проверить правила интерфейса, которые отсутствуют в модели."""

    @classmethod
    def setUpClass(cls):
        """Подготовить Tcl/Tk из установленного Python."""
        prepare_tk()

    def setUp(self):
        """Создать скрытое окно для изолированного сценария."""
        self.app = App()
        self.app.root.withdraw()

    def tearDown(self):
        """Освободить окно, таймеры и графические ресурсы."""
        self.app.root.destroy()

    def test_only_splash_click_starts(self):
        """Клавиши и щелчок вне заставки не начинают партию."""
        self.app.on_click(SimpleNamespace(x=20, y=20))
        self.app.on_key_down(SimpleNamespace(keysym="Return"))
        self.assertEqual(self.app.game.state, "menu")
        self.app.on_click(SimpleNamespace(x=400, y=300))
        self.assertEqual(self.app.game.state, "running")
        self.assertEqual(self.app.keys, set())

    def test_key_release_and_focus_loss(self):
        """Отпускание выключает двигатель, потеря фокуса включает паузу."""
        self.app.game.start()
        self.app.on_key_down(SimpleNamespace(keysym="Up"))
        self.app.game.update(0.01, self.app.keys)
        self.assertTrue(self.app.game.ship.thrust)
        self.app.on_key_up(SimpleNamespace(keysym="Up"))
        self.app.game.update(0.01, self.app.keys)
        self.assertFalse(self.app.game.ship.thrust)
        self.app.on_focus_out(None)
        self.assertTrue(self.app.paused)
        self.assertEqual(self.app.keys, set())

    def test_explosion_tiles_and_scene_render(self):
        """Тайлы имеют прозрачность и разные изображения по времени."""
        self.assertEqual(len(self.app.frames), cfg.EXPLOSION_FRAMES)
        first, last = self.app.frames[0], self.app.frames[-1]
        self.assertEqual(first.width(), cfg.TILE_SIZE)
        self.assertTrue(first.transparency_get(0, 0))
        middle = cfg.TILE_SIZE // 2
        self.assertFalse(first.transparency_get(middle + 5, middle))
        self.assertTrue(last.transparency_get(middle + 5, middle))
        self.app.game.start()
        self.app.game.spawn()
        self.app.game.fire()
        self.app.game.ship.thrust = True
        self.app.game.explosions = [Explosion(300, 300)]
        self.app.draw()
        self.assertGreater(len(self.app.canvas.find_all()), 100)


if __name__ == "__main__":
    unittest.main()
