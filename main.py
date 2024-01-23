import os
import pygame
import sys
import random
import math


# useful stuff

def load_image(name, scale=1):
    fullname = os.path.join('assets', name)
    try:
        image = pygame.image.load(fullname).convert_alpha()
        image = pygame.transform.scale_by(image, scale)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)
    return image


def play_sound(name):
    fullname = os.path.join('assets/sound', name)
    try:
        a = pygame.mixer.Sound(fullname)
        a.play()
    except pygame.error as message:
        print('Cannot load sound:', name)
        raise SystemExit(message)


def directional_move(pos, amount, rotation):
    return round(pos[0] + math.sin(math.radians(rotation)) * amount, 6), \
           round(pos[1] + math.cos(math.radians(rotation)) * amount, 6)


def fps_sync_int(numb, reversed=False):
    if reversed:
        return numb * 30 / FPS
    else:
        return numb / 30 * FPS


def collision_check(self_group_check, other_group_check):
    def real_func(self, other):
        for i in self.hitboxes:
            if i.group == self_group_check:
                for j in other.hitboxes:
                    if j.group == other_group_check:
                        x, y = (
                                       other.x - j.hitbox.get_width() / 2 + j.hitbox_offset[0]) - (
                                       self.x - i.hitbox.get_width() / 2 + i.hitbox_offset[0]), \
                               (other.y - j.hitbox.get_height() / 2 + j.hitbox_offset[1]) - (
                                       self.y - i.hitbox.get_height() / 2 + i.hitbox_offset[1])
                        if i.mask.overlap(j.mask, (x, y)):
                            return True
        return False

    return real_func


# weapon & entity presets

def melee_held_gen(x_offset=0, y_offset=0, rot_offset=0, flippable_x=False, flippable_y=False):
    def real_func(self):
        self.x = player.x
        self.y = player.y
        dx, dy = self.x + CAMERA.x - cursor.x, -(self.y + CAMERA.y - cursor.y)
        self.rotation = math.degrees(math.atan2(dy, dx))
        if (self.rotation + 270) % 360 >= 180 and flippable_y:
            self.flipy = 1
        else:
            self.flipy = 0
        if (self.rotation + 270) % 360 >= 180 and flippable_x:
            self.flipx = 1
        else:
            self.flipx = 0
        self.x, self.y = directional_move(
            (self.x, self.y), x_offset * (1 + self.flipy * 0), self.rotation)
        self.x, self.y = directional_move(
            (self.x, self.y), y_offset * (1 + self.flipx * 0), self.rotation + 90)
        self.rotation += rot_offset

    return real_func


def melee_attack_gen(
        x_offset=0,
        y_offset=0,
        rot_offset=0,
        prepare_speed=1.0,
        attack_rot=45.0,
        attack_ticks=1.0,
        end_speed=1.0):
    def real_func(self):
        a = attack_rot * (1 + self.flipx * -2) * -1
        self.rotation -= rot_offset
        if self.states['attack']['step'] == 'starting':
            self.states['attack']['start_rotation'] = self.rotation
            self.states['attack']['step'] = 'started'
        elif self.states['attack']['step'] == 'started':
            self.rotation += (self.states['attack']['start_rotation'] - a - self.rotation) \
                             * fps_sync_int(prepare_speed, reversed=True)
            if abs(self.states['attack']['start_rotation'] - a - self.rotation) < 0.05:
                self.rotation = self.states['attack']['start_rotation'] - a
                self.states['attack']['tick_rotation'] = (self.states['attack']['start_rotation']
                                                          + a - self.rotation) / fps_sync_int(attack_ticks)
                self.states['attack']['step'] = 'hitting'
        elif self.states['attack']['step'] == 'hitting':
            self.rotation += self.states['attack']['tick_rotation']
            for i in sprites_groups['entities']:
                damage_collision = collision_check('damage', 'damage')
                if damage_collision(player.holding_weapon, i) and i != player:
                    self.on_hit(i)
            if round(self.states['attack']['start_rotation'] + a - self.rotation, 5) == 0:
                self.states['attack']['step'] = 'ending'
        elif self.states['attack']['step'] == 'ending':
            self.rotation += (self.states['attack']['start_rotation'] - self.rotation) \
                             * fps_sync_int(end_speed, reversed=True)
            if abs(self.states['attack']['start_rotation'] - self.rotation) < 0.05:
                self.rotation = self.states['attack']['start_rotation']
                del self.states['attack']
        self.x = player.x
        self.y = player.y
        self.x, self.y = directional_move(
            (self.x, self.y), x_offset, self.rotation)
        self.x, self.y = directional_move(
            (self.x, self.y), y_offset, self.rotation + 90)
        self.rotation += rot_offset
        for i in self.hitboxes:
            i.render()

    return real_func


class Camera:
    def __init__(self):
        self.x, self.x_target = 0, 0
        self.y, self.y_target = 0, 0
        self.rotation = 0
        self.scale = 1
        self.mode = 'follow'
        self.speed = 1

    def set_mode(self, mode):
        self.mode = mode

    def update(self):
        if self.mode == 'follow':
            self.x = self.x_target
            self.y = self.y_target
        if self.mode == 'smooth_follow':
            self.x += (self.x_target - self.x) * self.speed
            self.y += (self.y_target - self.y) * self.speed
            if abs(self.x_target - self.x) < 0.01:
                self.x = self.x_target
            if abs(self.y_target - self.y) < 0.01:
                self.y = self.y_target

    def move(self, pos=(0, 0)):
        self.x_target = pos[0]
        self.y_target = pos[1]


class Hitbox(pygame.sprite.Sprite):
    def __init__(self, parent, group, htype, *args, **kwargs):
        super().__init__()
        self.parent = parent
        self.mask = None
        self.hitbox = None
        self.hitbox_offset = [0, 0]
        self.type = htype
        self.args = args
        self.kwargs = kwargs
        self.group = group
        self.render()

    def render(self):
        if 'x_offset' in self.kwargs.keys():
            self.hitbox_offset[0] = self.kwargs['x_offset']
        if 'y_offset' in self.kwargs.keys():
            self.hitbox_offset[1] = self.kwargs['y_offset']
        if self.type == 'image':
            orig_size = self.parent.costume[0][self.parent.cur_frame].get_size()
            self.hitbox = pygame.transform.rotate(pygame.transform.scale(
                self.parent.costume[0][self.parent.cur_frame],
                (self.parent.x_scale * orig_size[0],
                 self.parent.y_scale * orig_size[1])), self.parent.rotation)
            self.mask = pygame.mask.from_surface(self.hitbox)
        elif self.type == 'rect':
            self.hitbox = pygame.surface.Surface(self.kwargs['size'])
            self.hitbox.fill('red')
            orig_size = self.hitbox.get_size()
            self.hitbox = pygame.transform.rotate(pygame.transform.scale(
                self.hitbox,
                (self.parent.x_scale * orig_size[0],
                 self.parent.y_scale * orig_size[1])), self.parent.rotation)
            self.mask = pygame.mask.from_surface(self.hitbox)


class Object(pygame.sprite.Sprite):
    def __init__(
            self,
            layer,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(all_sprites, shown_sprites)
        shown_sprites.change_layer(self, layer)
        for i in groups:
            i.add(self)
        self.shown = True
        self.costumes = {}
        self.costume = None
        self.flipx = 0
        self.flipy = 0
        self.timer = 0
        self.states = dict()
        self.states['effects'] = dict()
        self.cur_costume_id = None
        self.costume_timer = 0
        self.image = None
        self.rect = None
        self.hitboxes = []
        self.x = 0
        self.y = 0
        self.cur_frame = 0
        self.layer_true = layer
        self.layer_offset = layer
        self.rotation = 0
        self.x_scale = 1
        self.y_scale = 1
        self.rect = pygame.rect.Rect(self.x, self.y, 0, 0)
        if sprite is not None:
            self.register_costume(
                'default',
                sprite,
                columns,
                rows,
                animation_speed)
            self.set_costume('default')
        else:
            self.register_costume(
                'empty',
                pygame.surface.Surface((0, 0)),
                1,
                1,
                animation_speed)
            self.set_costume('empty')

    def register_costume(
            self,
            costume_id='default',
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0):
        frames = []
        rect = pygame.Rect(0, 0, sprite.get_width() // columns,
                           sprite.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (rect.w * i, rect.h * j)
                frames.append(sprite.subsurface(pygame.Rect(
                    frame_location, rect.size)))

        self.costumes[costume_id] = (frames, animation_speed)

    def register_hitbox(self, hitbox):
        self.hitboxes.append(hitbox)

    def timer_reset(self):
        self.timer = 0

    def set_costume(self, costume_id):
        self.costume = self.costumes[costume_id]
        self.cur_costume_id = costume_id
        self.cur_frame = 0
        self.costume_timer = 0
        orig_size = self.costume[0][self.cur_frame].get_size()
        self.image = pygame.transform.rotate(pygame.transform.flip(
            pygame.transform.scale(self.costume[0][self.cur_frame],
                                   (self.x_scale * orig_size[0] * CAMERA.scale,
                                    self.y_scale * orig_size[1] * CAMERA.scale)),
            self.flipx, self.flipy), self.rotation + CAMERA.rotation)
        self.rect = pygame.rect.Rect(
            SCREEN.get_width() /
            2 +
            round(
                ((self.x *
                  math.sin(
                      math.radians(
                          CAMERA.rotation +
                          90)) +
                  self.y *
                  math.sin(
                      math.radians(
                          CAMERA.rotation))) *
                 CAMERA.scale -
                 self.image.get_width() /
                 2 +
                 (
                         CAMERA.x *
                         math.sin(
                             math.radians(
                                 CAMERA.rotation +
                                 90)) +
                         CAMERA.y *
                         math.sin(
                             math.radians(
                                 CAMERA.rotation))) *
                 CAMERA.scale),
                5),
            SCREEN.get_height() /
            2 +
            round(
                ((self.x *
                  math.cos(
                      math.radians(
                          CAMERA.rotation +
                          90)) +
                  self.y *
                  math.cos(
                      math.radians(
                          CAMERA.rotation))) *
                 CAMERA.scale -
                 self.image.get_height() /
                 2 +
                 (
                         CAMERA.x *
                         math.cos(
                             math.radians(
                                 CAMERA.rotation +
                                 90)) +
                         CAMERA.y *
                         math.cos(
                             math.radians(
                                 CAMERA.rotation))) *
                 CAMERA.scale),
                5),
            *
            self.image.get_size())

    def set_layer_offset(self, layer):
        self.layer_offset = layer

    def set_scales(self, x, y):
        self.x_scale, self.y_scale = x, y

    def set_position(self, x, y):
        self.x, self.y = x, y

    def set_rotation(self, angle):
        self.rotation = angle

    def set_anim_frame(self, frame):
        self.cur_frame = frame

    def tick_timer(self):
        self.timer += 1

    def render_costume(self):
        if self.rect.colliderect(pygame.rect.Rect(-50, -50, SCREEN.get_width() + 50, SCREEN.get_height() + 50)):
            orig_size = self.costume[0][self.cur_frame].get_size()
            self.image = pygame.transform.rotate(pygame.transform.flip(
                pygame.transform.scale(self.costume[0][self.cur_frame],
                                       (self.x_scale * orig_size[0] * CAMERA.scale,
                                        self.y_scale * orig_size[1] * CAMERA.scale)),
                self.flipx, self.flipy), self.rotation + CAMERA.rotation)
            if 'color' in self.states['effects'].keys():
                self.image.fill(self.states['effects']['color'], special_flags=pygame.BLEND_RGBA_MULT)
            if 'alpha' in self.states['effects'].keys():
                self.image.fill(pygame.color.Color(255, 255, 255, 255 - self.states['effects']['alpha']),
                                special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = pygame.rect.Rect(
            SCREEN.get_width() /
            2 +
            round(
                ((self.x *
                  math.sin(
                      math.radians(
                          CAMERA.rotation +
                          90)) +
                  self.y *
                  math.sin(
                      math.radians(
                          CAMERA.rotation))) *
                 CAMERA.scale -
                 self.image.get_width() /
                 2 +
                 (
                         CAMERA.x *
                         math.sin(
                             math.radians(
                                 CAMERA.rotation +
                                 90)) +
                         CAMERA.y *
                         math.sin(
                             math.radians(
                                 CAMERA.rotation))) *
                 CAMERA.scale),
                8),
            SCREEN.get_height() /
            2 +
            round(
                ((self.x *
                  math.cos(
                      math.radians(
                          CAMERA.rotation +
                          90)) +
                  self.y *
                  math.cos(
                      math.radians(
                          CAMERA.rotation))) *
                 CAMERA.scale -
                 self.image.get_height() /
                 2 +
                 (
                         CAMERA.x *
                         math.cos(
                             math.radians(
                                 CAMERA.rotation +
                                 90)) +
                         CAMERA.y *
                         math.cos(
                             math.radians(
                                 CAMERA.rotation))) *
                 CAMERA.scale),
                8),
            *
            self.image.get_size())

    def costume_anim(self):
        self.costume_timer += 1
        if self.costume[1] > 0:
            if self.costume_timer % (fps_sync_int(30) // self.costume[1]) == 0:
                self.cur_frame += 1
                self.costume_timer = 0
            if self.cur_frame >= len(self.costume[0]):
                self.cur_frame = 0

    def update(self):
        if self in shown_sprites:
            self.layer_true = self.y
            shown_sprites.change_layer(
                self, self.layer_true + self.layer_offset)
            for i in self.hitboxes:
                i.render()
        if self in shown_sprites and not self.shown:
            shown_sprites.remove(self)
        elif self not in shown_sprites and self.shown:
            shown_sprites.add(self)
        self.render_costume()


class PrimeObject(Object):
    def set_costume(self, costume_id):
        self.costume = self.costumes[costume_id]
        self.cur_costume_id = costume_id
        self.cur_frame = 0
        self.costume_timer = 0
        orig_size = self.costume[0][self.cur_frame].get_size()
        self.image = pygame.transform.rotate(pygame.transform.flip(
            pygame.transform.scale(self.costume[0][self.cur_frame],
                                   (self.x_scale * orig_size[0], self.y_scale * orig_size[1])),
            self.flipx, self.flipy), self.rotation)
        self.rect = pygame.rect.Rect(SCREEN.get_width() / 2 + self.x - self.image.get_width() / 2,
                                     SCREEN.get_height() / 2 + self.y - self.image.get_height() / 2,
                                     *self.image.get_size())
        self.image = pygame.transform.flip(self.image, self.flipx, self.flipy)

    def render_costume(self):
        if self.rect.colliderect(pygame.rect.Rect(-50, -50, SCREEN.get_width() + 50, SCREEN.get_height() + 50)):
            orig_size = self.costume[0][self.cur_frame].get_size()
            self.image = pygame.transform.rotate(pygame.transform.flip(
                pygame.transform.scale(self.costume[0][self.cur_frame],
                                       (self.x_scale * orig_size[0], self.y_scale * orig_size[1])),
                self.flipx, self.flipy), self.rotation)
            if 'color' in self.states['effects'].keys():
                self.image.fill(self.states['effects']['color'], special_flags=pygame.BLEND_RGBA_MULT)
            if 'alpha' in self.states['effects'].keys():
                self.image.fill(pygame.color.Color(255, 255, 255, 255 - self.states['effects']['alpha']),
                                special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = pygame.rect.Rect(
            SCREEN.get_width() /
            2 +
            self.x -
            self.image.get_width() /
            2,
            SCREEN.get_height() /
            2 +
            self.y -
            self.image.get_height() /
            2,
            *
            self.image.get_size())


class Block(Object):
    def __init__(
            self,
            layer,
            x=0,
            y=0,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(layer, sprite, columns, rows, animation_speed, groups)
        self.set_position(x, y)

    def set_position(self, x, y):
        self.x, self.y = x * 30, y * 30 - self.image.get_height() / 2 + 16


class TextGenerator(Object):
    def __init__(
            self,
            layer,
            x=0,
            y=0,
            size=14,
            every=0,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(layer, sprite, columns, rows, animation_speed, groups)
        self.set_position(x, y)
        self.text_size = size
        self.every = every
        self.states['typing'] = dict()
        self.states['letter'] = dict()
        self.states['typing']['step'] = 'waiting'
        self.states['typing']['every'] = 0
        self.text = ''

    def clear(self):
        for i in self.states['typing']['created']:
            i.kill()
            del i
        self.states['typing']['step'] = 'waiting'
        self.x = self.states['typing']['x']
        self.y = self.states['typing']['y']
        self.text = ''

    def register_font(
            self,
            sprite=None,
            columns=1,
            rows=1):
        frames = []
        rect = pygame.Rect(0, 0, sprite.get_width() // columns,
                           sprite.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (rect.w * i, rect.h * j)
                frames.append(sprite.subsurface(pygame.Rect(
                    frame_location, rect.size)))

        text_order = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz()[]_.,:;%!?~-+=1234567890'

        for i in range(len(frames)):
            self.costumes[text_order[i]] = ([frames[i]], 0)

    def on_tick(self):
        if self.text != '' and self.states['typing']['step'] == 'waiting':
            if self.every == 0:
                self.states['typing']['step'] = 'momental'
            else:
                self.states['typing']['step'] = 'going'
            self.states['typing']['letter'] = 0
            self.states['typing']['x'] = self.x
            self.states['typing']['y'] = self.y
            self.states['typing']['created'] = []
            self.states['letter']['color'] = '#FFFFFF'
            self.states['letter']['alpha'] = 0
            self.states['typing']['wait'] = 0
        if self.states['typing']['step'] == 'going' and self.states['typing']['every'] % self.every == 0:
            if self.states['typing']['wait'] > 0:
                self.states['typing']['wait'] -= 1
                return
            if self.text[self.states['typing']['letter']] == '<':
                self.commands_finc()
                return
            self.states['typing']['created'].append(TextLetter(self,
                                                               letter=self.text[self.states['typing']['letter']],
                                                               x=self.x, y=self.y))
            self.x += self.text_size
            self.states['typing']['letter'] += 1
            if self.states['typing']['letter'] >= len(self.text):
                self.states['typing']['step'] = 'done'
        if self.text != '' and self.states['typing']['step'] == 'momental':
            while self.states['typing']['step'] != 'done':
                if self.text[self.states['typing']['letter']] == '<':
                    self.commands_finc()
                    continue
                self.states['typing']['created'].append(TextLetter(self,
                                                                   letter=self.text[self.states['typing']['letter']],
                                                                   x=self.x, y=self.y))
                self.x += self.text_size
                self.states['typing']['letter'] += 1
                if self.states['typing']['letter'] >= len(self.text):
                    self.states['typing']['step'] = 'done'
        self.states['typing']['every'] += 1
        if self.every > 0:
            self.states['typing']['every'] %= self.every

    def commands_finc(self):
        self.states['typing']['letter'] += 1
        command = ''
        while self.text[self.states['typing']['letter']] != '>':
            command += self.text[self.states['typing']['letter']]
            self.states['typing']['letter'] += 1
        command = command.split(':')
        command_args = command[1].split(',') if len(command) > 1 else ''
        command = command[0]
        if command == 'col':
            self.states['letter']['color'] = command_args[0]
        if command == 'alp':
            self.states['letter']['alpha'] = int(command_args[0])
        if command == 'n':
            self.x = self.states['typing']['x']
            self.y += self.text_size
        if command == 'x':
            self.states['typing']['x'] = int(command_args[0])
            self.x = self.states['typing']['x']
        if command == 'y':
            self.y = self.states['typing']['y'] = int(command_args[0])
            self.y = self.states['typing']['y']
        if command == 'wait':
            self.states['typing']['wait'] = int(command_args[0])
        if command == 'd':
            for i in range(1, int(command_args[0]) + 1):
                self.states['typing']['created'][-i].kill()
                del self.states['typing']['created'][-i]
            self.states['typing']['every'] += 1
            if self.every > 0:
                self.states['typing']['every'] %= self.every
        self.states['typing']['letter'] += 1
        if self.states['typing']['letter'] >= len(self.text):
            self.states['typing']['step'] = 'done'


class TextLetter(Object):
    def __init__(
            self,
            parent,
            letter='',
            x=0,
            y=0):
        super().__init__(parent.layer_offset)
        self.parent = parent
        self.costumes = self.parent.costumes
        self.set_position(x, y)
        if letter != ' ':
            self.set_costume(letter)
        self.states['effects']['color'] = self.parent.states['letter']['color']
        self.states['effects']['alpha'] = self.parent.states['letter']['alpha']


class Entity(Object):
    def __init__(
            self,
            layer,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(layer, sprite, columns, rows, animation_speed, groups)
        self.speed = 4
        self.able_move = True
        self.facing = 'left'
        self.holding_weapon = None

    def entity_death(self):
        self.shown = False
        self.kill()


class entity_Player(Entity):
    def __init__(
            self,
            layer,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(layer, sprite, columns, rows, animation_speed, groups)
        self.base_hp = 100
        self.base_defense = 0
        self.register_costume('left', load_image('player_left.png', 2),
                              columns=1,
                              rows=1,
                              animation_speed=0)
        self.register_costume('walking_left', load_image('player_walk_left.png', 2),
                              columns=4,
                              rows=1,
                              animation_speed=8)
        self.register_costume('right', load_image('player_right.png', 2),
                              columns=1,
                              rows=1,
                              animation_speed=0)
        self.register_costume('walking_right', load_image('player_walk_right.png', 2),
                              columns=4,
                              rows=1,
                              animation_speed=8)
        self.register_costume('up', load_image('player_up.png', 2),
                              columns=1,
                              rows=1,
                              animation_speed=0)
        self.register_costume('walking_up', load_image('player_walk_up.png', 2),
                              columns=4,
                              rows=1,
                              animation_speed=8)
        self.register_costume('down', load_image('player_down.png', 2),
                              columns=1,
                              rows=1,
                              animation_speed=0)
        self.register_costume('walking_down', load_image('player_walk_down.png', 2),
                              columns=4,
                              rows=1,
                              animation_speed=8)
        self.set_costume('left')

    def on_tick(self):
        key = pygame.key.get_pressed()
        if key[pygame.K_DOWN] and self.able_move:
            if 'walking' not in self.cur_costume_id or self.facing not in self.cur_costume_id:
                frame = self.cur_frame
                timer = self.costume_timer
                self.set_costume(f'walking_{player.facing}')
                self.set_anim_frame(frame)
                self.costume_timer = timer
            self.y += player.speed * 30 / FPS
            self.update()
            while pygame.sprite.spritecollide(self,
                                              sprites_groups['walls'], False, collision_check('movement', 'movement')):
                self.y -= 1
                self.update()
        elif key[pygame.K_UP] and self.able_move:
            if 'walking' not in self.cur_costume_id or self.facing not in self.cur_costume_id:
                frame = self.cur_frame
                timer = self.costume_timer
                self.set_costume(f'walking_{player.facing}')
                self.set_anim_frame(frame)
                self.costume_timer = timer
            self.y -= player.speed * 30 / FPS
            self.update()
            while pygame.sprite.spritecollide(self,
                                              sprites_groups['walls'], False, collision_check('movement', 'movement')):
                self.y += 1
                self.update()
        if key[pygame.K_RIGHT] and self.able_move:
            if 'walking' not in self.cur_costume_id or player.facing not in player.cur_costume_id:
                frame = self.cur_frame
                timer = self.costume_timer
                self.set_costume(f'walking_{player.facing}')
                self.set_anim_frame(frame)
                self.costume_timer = timer
            self.x += player.speed * 30 / FPS
            self.update()
            while pygame.sprite.spritecollide(self,
                                              sprites_groups['walls'], False, collision_check('movement', 'movement')):
                self.x -= 1
                self.update()
        elif key[pygame.K_LEFT] and self.able_move:
            if 'walking' not in self.cur_costume_id or self.facing not in self.cur_costume_id:
                frame = self.cur_frame
                timer = self.costume_timer
                self.set_costume(f'walking_{player.facing}')
                self.set_anim_frame(frame)
                self.costume_timer = timer
            self.x -= player.speed * 30 / FPS
            self.update()
            while pygame.sprite.spritecollide(self,
                                              sprites_groups['walls'], False, collision_check('movement', 'movement')):
                self.x += 1
                self.update()
        if not (key[pygame.K_DOWN] or key[pygame.K_UP]
                or key[pygame.K_LEFT] or key[pygame.K_RIGHT]):
            if 'walking' in self.cur_costume_id:
                self.set_costume(f'{self.facing}')
        if pygame.mouse.get_focused():
            cursor.shown = True
            dx, dy = self.x + CAMERA.x - cursor.x, self.y + CAMERA.y - cursor.y
            if dx != 0:
                rot = math.degrees(math.atan2(dy, dx))
            else:
                if dy > 0:
                    rot = 90
                else:
                    rot = 270
            rot += 270
            rot %= 360
            if 45 > rot >= 0 or 360 > rot >= 315:
                self.facing = 'up'
            elif 135 > rot >= 45:
                self.facing = 'right'
            elif 225 > rot >= 135:
                self.facing = 'down'
            else:
                self.facing = 'left'
            if 'walking' not in player.cur_costume_id:
                self.set_costume(f'{player.facing}')
        else:
            cursor.shown = False


class weapon_BirchTree(Object):
    def __init__(
            self,
            layer,
            sprite=None,
            columns=1,
            rows=1,
            animation_speed=1.0,
            groups=()):
        super().__init__(layer, sprite, columns, rows, animation_speed, groups)
        self.object_id = 'BirchTree'
        self.held = melee_held_gen(x_offset=0, y_offset=-124, rot_offset=90, flippable_x=True)
        self.attack = melee_attack_gen(x_offset=0, y_offset=-124, rot_offset=90,
                                       prepare_speed=0.08, attack_rot=45, attack_ticks=3,
                                       end_speed=0.2)
        self.register_hitbox(Hitbox(self, 'damage', 'image'))

    def left_click_interact(self):
        if 'attack' not in self.states.keys():
            self.states['attack'] = {'step': 'starting'}

    def on_hit(self, other):
        play_sound('sus.ogg')
        other.entity_death()

    def update(self):
        if player.holding_weapon == self:
            self.shown = True
            for i in self.hitboxes:
                i.render()
            if 'attack' not in self.states.keys():
                self.held(self)
            else:
                self.attack(self)
        else:
            self.shown = False
        if self in shown_sprites:
            self.layer_true = self.y
            shown_sprites.change_layer(
                self, self.layer_true + self.layer_offset)
        if self in shown_sprites and not self.shown:
            shown_sprites.remove(self)
        elif self not in shown_sprites and self.shown:
            shown_sprites.add(self)
        self.render_costume()


class Room:
    def on_set(self):
        pass

    def room_function(self):
        pass

    def set(self):
        global CAMERA, CLOCK, FPS, SCREEN, RUNNING, CURRENT_ROOM, GAME_DATA
        global sprites_groups, all_sprites, shown_sprites
        CLOCK = pygame.time.Clock()
        FPS = 60
        all_sprites = pygame.sprite.Group()
        shown_sprites = pygame.sprite.LayeredUpdates()
        sprites_groups = dict()

        CAMERA = Camera()
        if self.on_set is not None:
            self.on_set()


class room_Testing(Room):
    def on_set(self):
        global CAMERA, CLOCK, FPS, SCREEN, RUNNING, CURRENT_ROOM, GAME_DATA
        global sprites_groups, all_sprites, shown_sprites
        global cursor, ground, wall, entity, player

        self.timer = 0

        CAMERA.set_mode('smooth_follow')
        CAMERA.speed = 0.2
        CAMERA.scale = 1

        sprites_groups['walls'] = pygame.sprite.Group()
        sprites_groups['entities'] = pygame.sprite.Group()

        cursor = PrimeObject(10000,
                             sprite=load_image('crs_default.png', 2),
                             columns=1,
                             rows=1,
                             animation_speed=0)

        ground = [[Block(0,
                         sprite=load_image('ground.png', 2),
                         columns=2,
                         rows=1,
                         animation_speed=0,
                         x=j - 12,
                         y=i - 4) for j in range(25)] for i in range(9)]
        wall = [[Block(48,
                       sprite=load_image('wall.png', 2),
                       x=j - 12,
                       y=i - 4,
                       columns=2,
                       rows=1,
                       animation_speed=0,
                       groups=(sprites_groups['walls'],))
                 for j in range(25) if i == 0 or j == 0 or i == 8 or j == 24] for i in range(9)]
        player = entity_Player(48,
                               sprite=load_image('default_object.png', 2),
                               columns=1,
                               rows=1,
                               animation_speed=0)

        for i in sprites_groups['walls']:
            i.register_hitbox(Hitbox(i, 'movement', 'rect', size=(32, 32)))
        player.register_hitbox(Hitbox(player, 'movement', 'rect', size=(28, 28), y_offset=4))

        player.holding_weapon = weapon_BirchTree(256, sprite=load_image('wpn_tree.png', 2),
                                                 columns=1,
                                                 rows=1,
                                                 animation_speed=0)

        entity = [Entity(48,
                         sprite=load_image('entity_test.png', 2),
                         columns=1,
                         rows=1,
                         animation_speed=0,
                         groups=(sprites_groups['entities'],))]
        entity[0].register_hitbox(Hitbox(entity[0], 'damage', 'image'))

        all_sprites.update()

    def room_function(self):
        global CAMERA, CLOCK, FPS, SCREEN, RUNNING, CURRENT_ROOM, GAME_DATA
        global sprites_groups, all_sprites, shown_sprites
        global cursor, ground, wall, entity, player

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                RUNNING = False
            if event.type == pygame.MOUSEMOTION:
                cursor.x = event.pos[0] - SCREEN.get_width() / 2
                cursor.y = event.pos[1] - SCREEN.get_height() / 2
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    player.holding_weapon.left_click_interact()
                elif event.button == 2:
                    entity = [Entity(48,
                                     sprite=load_image('entity_test.png', 2),
                                     columns=1,
                                     rows=1,
                                     animation_speed=0,
                                     groups=(sprites_groups['entities'],))]
                    entity[0].register_hitbox(Hitbox(entity[0], 'damage', 'image'))
                    entity[0].x = 360 * (random.random() - 0.5)
                elif event.button == 3:
                    text = TextGenerator(5000, x=0, y=0, every=1)
                    text.register_font(sprite=load_image('fonts/normal_font.png', 2), columns=26, rows=3)
                    text.text = 'hello guys'

        CAMERA.move((-player.x, -player.y))

        self.timer += 1


class room_Intro(Room):
    def on_set(self):
        global CAMERA, CLOCK, FPS, SCREEN, RUNNING, CURRENT_ROOM, GAME_DATA
        global sprites_groups, all_sprites, shown_sprites
        global text

        self.timer = 0

        CAMERA.set_mode('smooth_follow')
        CAMERA.speed = 0.2
        CAMERA.scale = 1

        text = TextGenerator(5000, x=0, y=0, every=fps_sync_int(1))
        text.register_font(sprite=load_image('fonts/normal_font.png', 2), columns=26, rows=3)

        all_sprites.update()

    def room_function(self):
        global CAMERA, CLOCK, FPS, SCREEN, RUNNING, CURRENT_ROOM, GAME_DATA
        global sprites_groups, all_sprites, shown_sprites
        global text

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                RUNNING = False

        if self.timer == fps_sync_int(30):
            line = 'welcome to...'
            say = f'<x:{len(line) * -7}>{line}'
            text.text = say

        if self.timer == fps_sync_int(120):
            text.clear()
            line = 'totally serious dungeon cleaning game'
            say = f'<x:{len(line) * -7}>{line}'
            text.text = say

        if self.timer == fps_sync_int(210):
            text.clear()
            lines = [
                'but first of all...<wait:30>',
                'you must read this funny unskippable thing'
            ]
            say = ''
            for i in lines:
                visible_len = 0
                record = True
                for j in i:
                    if j == '<':
                        record = False
                    elif j == '>':
                        record = True
                    if record:
                        visible_len += 1
                say += f'<x:{visible_len * -7}>{i}<n>'
            text.text = say

        if self.timer == fps_sync_int(390):
            text.clear()
            lines = [
                'good luck<wait:30>',
                'my player'
            ]
            say = ''
            for i in lines:
                visible_len = 0
                record = True
                for j in i:
                    if j == '<':
                        record = False
                    if record:
                        visible_len += 1
                    elif j == '>':
                        record = True
                say += f'<x:{visible_len * -7}>{i}<n>'
            text.text = say

        if self.timer == fps_sync_int(480):
            text.every = 0
            text.clear()
            text.y = 380
            lines = [
                'rule 1. no genshin impact',
                'rule 2. no friday night funkin',
                'rule 3. no vtubers',
                'rule 4. no madness combat',
                'rule 5. no dream smp',
                'rule 6. no nsfw please my mom checks the internet',
                'rule 7. no touhou',
                'rule 8. no scp',
                'rule 9. no neco-arc',
                'rule 10. no binding of isaac',
                'rule 11. no league of legends',
                'rule 12. no osu',
                'rule 13. no undertale',
                'rule 14. no deltarune',
                'rule 15. no furrys',
                'rule 16. no valorant',
                'rule 17. no jujutsu kaisen',
                'rule 18. no gumball',
                'rule 19. no my hero academia',
                'rule 20. no roblox',
                'rule 21. no team fortress 2',
                'rule 22. no counter strike 1.6',
                'rule 23. no jojo references',
                'rule 24. no squid games',
                'rule 25. no jokes',
                'rule 26. no funny',
                'rule 27. no dota',
                'rule 28. no overwatch',
                'rule 29. no minecraft',
                'rule 30. no brawl stars',
                'rule 31. no clash royale',
                'rule 32. no clash of clans',
                'rule 33. no king of thieves',
                'rule 34. ignore rule 6'
            ]
            say = ''
            for i in lines:
                visible_len = 0
                record = True
                for j in i:
                    if j == '<':
                        record = False
                    if record:
                        visible_len += 1
                    elif j == '>':
                        record = True
                say += f'<x:{visible_len * -7}>{i}<n><n>'
            text.text = say

        if fps_sync_int(480) < self.timer < fps_sync_int(2130):
            CAMERA.speed = 1
            CAMERA.y_target -= fps_sync_int(1, reversed=True)

        if self.timer == fps_sync_int(2130):
            CAMERA.y_target = 0
            text.every = fps_sync_int(1)
            text.clear()
            text.y = 0
            lines = [
                'good job<wait:30>',
                '<col:#00FF00>now i allow you to pass'
            ]
            say = ''
            for i in lines:
                visible_len = 0
                record = True
                for j in i:
                    if j == '<':
                        record = False
                    if record:
                        visible_len += 1
                    elif j == '>':
                        record = True
                say += f'<x:{visible_len * -7}>{i}<n>'
            text.text = say

        if self.timer == fps_sync_int(2320):
            GAME_DATA['intro'] = 'yes'
            CURRENT_ROOM = room_Testing()
            CURRENT_ROOM.set()

        self.timer += 1


if __name__ == '__main__':
    # main script
    if "data" not in os.listdir():
        save = open("data", 'w')
        save.write('intro=no')
        save.close()
    save = open("data", 'r')
    GAME_DATA = dict()
    for i in save.read().split('\n'):
        GAME_DATA[i.split('=')[0]] = i.split('=')[1]
    save.close()

    pygame.init()
    pygame.mouse.set_visible(False)
    SCREEN = pygame.display.set_mode((800, 600))
    RUNNING = True
    CAMERA = Camera()
    CLOCK = pygame.time.Clock()
    FPS = 60

    all_sprites = pygame.sprite.Group()
    shown_sprites = pygame.sprite.LayeredUpdates()
    sprites_groups = dict()

    if GAME_DATA['intro'] == 'no':
        CURRENT_ROOM = room_Intro()
    else:
        CURRENT_ROOM = room_Testing()  # menu will be added soon
    CURRENT_ROOM.set()

    while RUNNING:
        CURRENT_ROOM.room_function()
        for i in all_sprites:
            if hasattr(i, 'on_tick'):
                i.on_tick()

        SCREEN.fill((0, 0, 0))

        CAMERA.update()
        all_sprites.update()
        for i in all_sprites:
            i.costume_anim()
            i.tick_timer()

        shown_sprites.draw(SCREEN)

        pygame.display.flip()
        CLOCK.tick(FPS)
    # working saving system
    save = open("data", 'w')
    save.write('\n'.join([f'{i}={GAME_DATA[i]}' for i in GAME_DATA.keys()]))
    save.close()
    pygame.quit()
