"""Проверки тороидальной физики и правил «Астероидов»."""

import math
import random
import unittest

import config as cfg
from models import Asteroid, Body, Explosion, Game, Missile, Ship, touches


class PhysicsTests(unittest.TestCase):
    """Проверить движение и столкновения, включая швы поля."""

    def test_wrapping_preserves_velocities(self):
        """Переход через обе границы не меняет скорости."""
        body = Body(cfg.WIDTH - 1, 1, 20, -20, spin=2)
        body.move(0.1)
        self.assertAlmostEqual(body.x, 1)
        self.assertAlmostEqual(body.y, cfg.HEIGHT - 1)
        self.assertEqual((body.vx, body.vy, body.spin), (20, -20, 2))

    def test_collision_across_corner(self):
        """Объекты в противоположных углах соприкасаются на торе."""
        self.assertTrue(touches(Body(1, 1),
                                Body(cfg.WIDTH - 1, cfg.HEIGHT - 1)))
        self.assertFalse(touches(Body(100, 100), Body(200, 200)))

    def test_drag_stops_ship_completely(self):
        """Без двигателя скорость уменьшается до точного нуля."""
        ship = Ship(300, 300, vx=40)
        ship.update(0.1, set())
        self.assertLess(ship.vx, 40)
        for _ in range(100):
            ship.update(0.1, set())
        self.assertEqual((ship.vx, ship.vy), (0, 0))

    def test_engine_and_speed_limit(self):
        """Ускорение следует направлению корабля и ограничено сверху."""
        ship = Ship(300, 300, angle=math.pi / 2)
        for _ in range(100):
            ship.update(0.1, {"Up"})
        self.assertTrue(ship.thrust)
        self.assertAlmostEqual(ship.vx, 0)
        self.assertAlmostEqual(ship.vy, cfg.MAX_SPEED)

    def test_missile_range_is_less_than_short_side(self):
        """Время жизни не позволяет ракете пересечь всё поле."""
        self.assertLess(cfg.MISSILE_SPEED * cfg.MISSILE_LIFETIME,
                        min(cfg.WIDTH, cfg.HEIGHT))


class GameTests(unittest.TestCase):
    """Проверить выстрелы, урон, генерацию и повторный запуск."""

    def setUp(self):
        """Подготовить воспроизводимую партию."""
        self.game = Game(random.Random(11))
        self.game.start()

    def test_missile_starts_at_nose_with_fixed_speed(self):
        """Скорость корабля не добавляется к скорости ракеты."""
        self.game.ship.vx = 150
        self.game.fire()
        missile = self.game.missiles[0]
        self.assertAlmostEqual(missile.x, self.game.ship.x)
        self.assertLess(missile.y, self.game.ship.y)
        self.assertAlmostEqual(math.hypot(missile.vx, missile.vy),
                               cfg.MISSILE_SPEED)
        self.game.fire()
        self.assertEqual(len(self.game.missiles), 1)

    def test_missile_expires(self):
        """Ракета удаляется после истечения времени жизни."""
        self.game.fire()
        for _ in range(100):
            self.game.update(0.01, set())
        self.assertEqual(self.game.missiles, [])

    def test_hit_awards_one_point_and_one_explosion(self):
        """Одна ракета уничтожает ровно один из наложенных астероидов."""
        self.game.asteroids = [Asteroid(100, 100), Asteroid(100, 100)]
        self.game.missiles = [Missile(100, 100)]
        self.game.update(0.001, set())
        self.assertEqual(self.game.score, 1)
        self.assertEqual(len(self.game.asteroids), 1)
        self.assertEqual(len(self.game.explosions), 1)
        self.assertEqual(self.game.missiles, [])

    def test_asteroids_pass_through_each_other(self):
        """Совпадающие астероиды не уничтожают друг друга."""
        self.game.asteroids = [Asteroid(100, 100), Asteroid(100, 100)]
        self.game.update(0.01, set())
        self.assertEqual(len(self.game.asteroids), 2)

    def test_zero_lives_ends_on_next_collision(self):
        """Буквальное правило задания: 3 → 2 → 1 → 0 → конец."""
        self.game.score = 7
        for expected in (2, 1, 0):
            self.game.ship.shield = 0
            self.game.asteroids = [Asteroid(cfg.WIDTH / 2, cfg.HEIGHT / 2)]
            self.game.update(0.001, set())
            self.assertEqual(self.game.lives, expected)
            self.assertEqual(self.game.state, "running")
            self.assertEqual((self.game.ship.vx, self.game.ship.vy), (0, 0))
        self.game.ship.shield = 0
        self.game.asteroids = [Asteroid(cfg.WIDTH / 2, cfg.HEIGHT / 2)]
        self.game.update(0.001, set())
        self.assertEqual(self.game.state, "over")
        self.assertEqual(self.game.score, 7)
        self.assertEqual(self.game.lives, 0)
        self.assertIsNone(self.game.ship)
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(self.game.missiles, [])

    def test_shield_prevents_immediate_second_death(self):
        """Защита после рождения не даёт потерять все жизни за кадр."""
        self.game.asteroids = [Asteroid(cfg.WIDTH / 2, cfg.HEIGHT / 2)]
        self.game.update(0.01, set())
        self.assertEqual(self.game.lives, 3)

    def test_spawn_has_varied_motion_and_limit(self):
        """Генератор задаёт разные скорости и соблюдает лимит объектов."""
        for _ in range(50):
            self.game.spawn()
        self.assertEqual(len(self.game.asteroids), cfg.MAX_ASTEROIDS)
        self.assertGreater(len({r.spin for r in self.game.asteroids}), 1)
        self.assertTrue(all(cfg.ASTEROID_MIN_SPEED <= math.hypot(r.vx, r.vy)
                            <= cfg.ASTEROID_MAX_SPEED
                            for r in self.game.asteroids))

    def test_restart_resets_objects_and_counters(self):
        """Новая партия сбрасывает накопленное состояние."""
        self.game.fire()
        self.game.spawn()
        self.game.score = 9
        self.game.lives = 0
        self.game.start()
        self.assertEqual((self.game.score, self.game.lives), (0, 3))
        self.assertEqual(self.game.asteroids, [])
        self.assertEqual(self.game.missiles, [])

    def test_explosion_advances_and_disappears(self):
        """Тайлы сменяются, завершённая анимация удаляется."""
        explosion = Explosion(100, 100)
        self.game.explosions = [explosion]
        self.assertEqual(explosion.frame, 0)
        self.game.update(cfg.EXPLOSION_DURATION / 2, set())
        self.assertEqual(explosion.frame, cfg.EXPLOSION_FRAMES // 2)
        self.game.update(cfg.EXPLOSION_DURATION / 2, set())
        self.assertEqual(self.game.explosions, [])


if __name__ == "__main__":
    unittest.main()
