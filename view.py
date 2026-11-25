import math
import random
import time
import tkinter as tk

import config as cfg
from models import Game


def polygon_points(x, y, radius, angle, outline):
    points = []
    for i, scale in enumerate(outline):
        phase = angle + i * math.tau / len(outline)
        points.extend((x + math.cos(phase) * radius * scale,
                       y + math.sin(phase) * radius * scale))
    return points


class App:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Астероиды • Сулимов Л. И. • ПИ25-2")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=cfg.WIDTH,
                                height=cfg.HEIGHT, bg=cfg.BG,
                                highlightthickness=0)
        self.canvas.pack()
        self.game = Game()
        self.keys = set()
        self.paused = False
        self.background_offset = 0
        rng = random.Random(33)
        self.stars = [(rng.randrange(cfg.WIDTH), rng.randrange(cfg.HEIGHT),
                       rng.choice((1, 1, 2))) for _ in range(110)]
        self.background_rocks = [
            (rng.randrange(cfg.WIDTH), rng.randrange(cfg.HEIGHT),
             rng.randrange(45, 100), rng.random() * math.tau)
            for _ in range(7)
        ]
        self.frames = self.make_explosion_tiles()
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.focus_set()
        self.last_time = time.perf_counter()
        self.tick()

    def run(self):
        self.root.mainloop()

    def make_explosion_tiles(self):
        size = cfg.TILE_SIZE
        sheet = tk.PhotoImage(width=size * cfg.EXPLOSION_FRAMES,
                              height=size)
        for frame in range(cfg.EXPLOSION_FRAMES):
            progress = frame / (cfg.EXPLOSION_FRAMES - 1)
            radius = 5 + progress * (size / 2 - 8)
            thickness = 8 * (1 - progress) + 2
            for y in range(size):
                for x in range(size):
                    dist = math.hypot(x - size / 2, y - size / 2)
                    if abs(dist - radius) < thickness:
                        green = int(220 * (1 - progress) + 35)
                        color = f"#ff{green:02x}45"
                        sheet.put(color, (frame * size + x, y))
        frames = []
        for frame in range(cfg.EXPLOSION_FRAMES):
            tile = tk.PhotoImage(width=size, height=size)
            tile.tk.call(str(tile), "copy", str(sheet), "-from",
                         frame * size, 0, (frame + 1) * size, size)
            frames.append(tile)
        self.explosion_sheet = sheet
        return frames

    def on_click(self, event):
        x1, y1, x2, y2 = cfg.SPLASH
        if (self.game.state in ("menu", "over")
                and x1 <= event.x <= x2 and y1 <= event.y <= y2):
            self.keys.clear()
            self.paused = False
            self.game.start()

    def on_key_down(self, event):
        key = event.keysym
        if key.lower() == "p" and key not in self.keys:
            if self.game.state == "running":
                self.paused = not self.paused
        elif key == "Escape":
            self.root.destroy()
            return
        self.keys.add(key)

    def on_key_up(self, event):
        self.keys.discard(event.keysym)

    def on_focus_out(self, event):
        self.keys.clear()
        if self.game.state == "running":
            self.paused = True

    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last_time, 0.1)
        self.last_time = now
        self.background_offset = (self.background_offset
                                  + cfg.BACKGROUND_SPEED * dt) % cfg.WIDTH
        if not self.paused:
            remaining = dt
            while remaining > 0:
                step = min(remaining, 1 / 120)
                self.game.update(step, self.keys)
                remaining -= step
        self.draw()
        self.root.after(round(1000 / cfg.FPS), self.tick)

    def text(self, x, y, value, size=12, color=cfg.TEXT, anchor="center"):
        self.canvas.create_text(x, y, text=value, fill=color,
                                font=("Segoe UI", size), anchor=anchor)

    def copies(self, x, y, radius):
        for dx in (-cfg.WIDTH, 0, cfg.WIDTH):
            for dy in (-cfg.HEIGHT, 0, cfg.HEIGHT):
                px, py = x + dx, y + dy
                if (-radius <= px <= cfg.WIDTH + radius
                        and -radius <= py <= cfg.HEIGHT + radius):
                    yield px, py

    def draw_background(self):
        c = self.canvas
        for x, y, size in self.stars:
            c.create_oval(x, y, x + size, y + size,
                          fill="#53647d", outline="")
        for x, y, radius, angle in self.background_rocks:
            x = (x - self.background_offset) % cfg.WIDTH
            for px, py in self.copies(x, y, radius):
                points = polygon_points(px, py, radius, angle,
                                        (1, .75, .9, .7, 1, .8, .95))
                c.create_polygon(points, fill="#26364d", stipple="gray50",
                                 outline="#1b293d")

    def draw_ship(self):
        ship = self.game.ship
        c = self.canvas
        for x, y in self.copies(ship.x, ship.y, 32):
            cosine, sine = math.cos(ship.angle), math.sin(ship.angle)

            def transform(vertices):
                result = []
                for px, py in vertices:
                    result.extend((x + px * cosine - py * sine,
                                   y + px * sine + py * cosine))
                return result

            if ship.thrust:
                c.create_polygon(transform(((-12, -7), (-31, 0), (-12, 7))),
                                 fill="#ffad70", outline="")
                c.create_polygon(transform(((-12, -3), (-23, 0), (-12, 3))),
                                 fill="#fff3b0", outline="")
            c.create_polygon(transform(((22, 0), (-14, -13), (-8, 0),
                                         (-14, 13))),
                             fill="#17384a", outline=cfg.ACCENT, width=2)
            if ship.shield > 0:
                c.create_oval(x - 28, y - 28, x + 28, y + 28,
                              outline="#376b87", dash=(4, 5))

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.draw_background()
        if self.game.state == "running":
            for rock in self.game.asteroids:
                for x, y in self.copies(rock.x, rock.y, rock.radius):
                    c.create_polygon(polygon_points(
                        x, y, rock.radius, rock.angle, rock.outline),
                        fill="#253247", outline="#9aacc2", width=2)
            for missile in self.game.missiles:
                for x, y in self.copies(missile.x, missile.y, 4):
                    c.create_oval(x - 3, y - 3, x + 3, y + 3,
                                  fill="#ffe7a0", outline="")
            self.draw_ship()
            for explosion in self.game.explosions:
                for x, y in self.copies(explosion.x, explosion.y,
                                        cfg.TILE_SIZE / 2):
                    c.create_image(x, y, image=self.frames[explosion.frame])
        c.create_rectangle(0, 0, cfg.WIDTH, 83,
                           fill="#101b2d", outline="")
        self.text(25, 25, "ЛАБОРАТОРНАЯ 3.4  /  ПИ25-2", 10,
                  cfg.MUTED, "w")
        self.text(25, 57, "АСТЕРОИДЫ", 23, cfg.ACCENT, "w")
        self.text(cfg.WIDTH - 235, 25, "ОЧКИ", 10, cfg.MUTED)
        self.text(cfg.WIDTH - 235, 56, f"{self.game.score:03d}", 23)
        self.text(cfg.WIDTH - 95, 25, "ЖИЗНИ", 10, cfg.MUTED)
        self.text(cfg.WIDTH - 95, 56, str(self.game.lives), 23)
        self.text(cfg.WIDTH / 2, cfg.HEIGHT - 22,
                  "← → — поворот    ↑ — двигатель    Пробел — огонь"
                  "    P — пауза    Esc — выход", 11, cfg.MUTED)
        if self.game.state != "running":
            c.create_rectangle(*cfg.SPLASH, fill="#122139",
                               outline=cfg.ACCENT, width=2)
            title = ("АСТЕРОИДЫ" if self.game.state == "menu"
                     else "ПОЛЁТ ЗАВЕРШЁН")
            self.text(cfg.WIDTH / 2, 260, title, 31, cfg.ACCENT)
            self.text(cfg.WIDTH / 2, 315,
                      "Нажмите на эту панель, чтобы начать", 15)
            self.text(cfg.WIDTH / 2, 360,
                      "Ускоряйтесь. Маневрируйте. Попадайте в цель.", 12,
                      cfg.MUTED)
            self.text(cfg.WIDTH / 2, 403,
                      "Сулимов Лев Игоревич  •  ПИ25-2", 11, cfg.MUTED)
        elif self.paused:
            c.create_rectangle(310, 275, 650, 365,
                               fill="#122139", outline=cfg.ACCENT)
            self.text(cfg.WIDTH / 2, 305, "ПАУЗА", 24, cfg.ACCENT)
            self.text(cfg.WIDTH / 2, 342, "P — продолжить", 12)
