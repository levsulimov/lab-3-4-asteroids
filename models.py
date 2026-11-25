from dataclasses import dataclass
import math
import random

import config as cfg


def distance(a, b):
    dx = abs(a.x - b.x) % cfg.WIDTH
    dy = abs(a.y - b.y) % cfg.HEIGHT
    return math.hypot(min(dx, cfg.WIDTH - dx),
                      min(dy, cfg.HEIGHT - dy))


def touches(a, b):
    return distance(a, b) <= a.radius + b.radius


@dataclass
class Body:

    x: float
    y: float
    vx: float = 0
    vy: float = 0
    angle: float = 0
    spin: float = 0
    radius: float = 10

    def move(self, dt):
        self.x = (self.x + self.vx * dt) % cfg.WIDTH
        self.y = (self.y + self.vy * dt) % cfg.HEIGHT
        self.angle = (self.angle + self.spin * dt) % math.tau


@dataclass
class Ship(Body):

    radius: float = cfg.SHIP_RADIUS
    shield: float = 0
    thrust: bool = False

    def update(self, dt, keys):
        self.spin = (int("Right" in keys) - int("Left" in keys))
        self.spin *= cfg.TURN_SPEED
        self.thrust = "Up" in keys
        if self.thrust:
            self.vx += math.cos(self.angle) * cfg.ACCELERATION * dt
            self.vy += math.sin(self.angle) * cfg.ACCELERATION * dt
        else:
            factor = math.exp(-cfg.DRAG * dt)
            self.vx *= factor
            self.vy *= factor
            if math.hypot(self.vx, self.vy) < cfg.STOP_SPEED:
                self.vx = self.vy = 0
        speed = math.hypot(self.vx, self.vy)
        if speed > cfg.MAX_SPEED:
            self.vx *= cfg.MAX_SPEED / speed
            self.vy *= cfg.MAX_SPEED / speed
        self.shield = max(0, self.shield - dt)
        self.move(dt)


@dataclass
class Asteroid(Body):

    outline: tuple = ()


@dataclass
class Missile(Body):

    radius: float = 3
    life: float = cfg.MISSILE_LIFETIME


@dataclass
class Explosion:

    x: float
    y: float
    age: float = 0

    @property
    def frame(self):
        fraction = self.age / cfg.EXPLOSION_DURATION
        return min(cfg.EXPLOSION_FRAMES - 1,
                   int(fraction * cfg.EXPLOSION_FRAMES))


class Game:

    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.score = 0
        self.lives = cfg.INITIAL_LIVES
        self.state = "menu"
        self.ship = None
        self.asteroids = []
        self.missiles = []
        self.explosions = []
        self.spawn_timer = 0
        self.fire_timer = 0

    def start(self):
        self.score = 0
        self.lives = cfg.INITIAL_LIVES
        self.state = "running"
        self.asteroids.clear()
        self.missiles.clear()
        self.explosions.clear()
        self.spawn_timer = 0
        self.fire_timer = 0
        self.respawn()

    def respawn(self):
        self.ship = Ship(cfg.WIDTH / 2, cfg.HEIGHT / 2,
                         angle=-math.pi / 2, shield=cfg.RESPAWN_SHIELD)

    def spawn(self):
        if len(self.asteroids) >= cfg.MAX_ASTEROIDS:
            return
        for _ in range(30):
            rock = Asteroid(
                self.rng.uniform(0, cfg.WIDTH),
                self.rng.uniform(0, cfg.HEIGHT),
                radius=self.rng.uniform(cfg.ASTEROID_MIN_RADIUS,
                                        cfg.ASTEROID_MAX_RADIUS),
            )
            if distance(rock, self.ship) >= cfg.SPAWN_CLEARANCE:
                break
        else:
            return
        heading = self.rng.uniform(0, math.tau)
        speed = self.rng.uniform(cfg.ASTEROID_MIN_SPEED,
                                 cfg.ASTEROID_MAX_SPEED)
        rock.vx = math.cos(heading) * speed
        rock.vy = math.sin(heading) * speed
        rock.spin = self.rng.uniform(-cfg.ASTEROID_MAX_SPIN,
                                     cfg.ASTEROID_MAX_SPIN)
        rock.outline = tuple(self.rng.uniform(0.72, 1) for _ in range(11))
        self.asteroids.append(rock)

    def fire(self):
        if self.state != "running" or self.fire_timer > 0:
            return
        ship = self.ship
        dx, dy = math.cos(ship.angle), math.sin(ship.angle)
        self.missiles.append(Missile(
            (ship.x + dx * (ship.radius + 5)) % cfg.WIDTH,
            (ship.y + dy * (ship.radius + 5)) % cfg.HEIGHT,
            dx * cfg.MISSILE_SPEED, dy * cfg.MISSILE_SPEED,
            angle=ship.angle,
        ))
        self.fire_timer = cfg.FIRE_INTERVAL

    def hit_ship(self, rock):
        self.asteroids.remove(rock)
        self.explosions.append(Explosion(rock.x, rock.y))
        if self.lives == 0:
            self.state = "over"
            self.ship = None
            self.asteroids.clear()
            self.missiles.clear()
            self.explosions.clear()
        else:
            self.lives -= 1
            self.respawn()

    def update(self, dt, keys):
        if self.state != "running":
            return
        self.fire_timer = max(0, self.fire_timer - dt)
        self.ship.update(dt, keys)
        if "space" in keys:
            self.fire()
        self.spawn_timer += dt
        if self.spawn_timer >= cfg.SPAWN_INTERVAL:
            self.spawn_timer %= cfg.SPAWN_INTERVAL
            self.spawn()
        for explosion in self.explosions:
            explosion.age += dt
        self.explosions = [e for e in self.explosions
                           if e.age < cfg.EXPLOSION_DURATION]
        for rock in self.asteroids:
            rock.move(dt)
        for missile in self.missiles:
            missile.move(dt)
            missile.life -= dt
        self.missiles = [m for m in self.missiles if m.life > 0]
        for missile in self.missiles[:]:
            for rock in self.asteroids[:]:
                if touches(missile, rock):
                    self.missiles.remove(missile)
                    self.asteroids.remove(rock)
                    self.explosions.append(Explosion(rock.x, rock.y))
                    self.score += 1
                    break
        if self.ship.shield <= 0:
            for rock in self.asteroids[:]:
                if touches(self.ship, rock):
                    self.hit_ship(rock)
                    break
