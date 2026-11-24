"""CASA scene inventory. Source references identify objects in the original scene.

Bindings describe available models only; they do not imply live state synchronization.
Unbound devices remain software simulations until a suitable model is added.
"""
from copy import deepcopy

from homate.modules.home.domain.device import Device

SCENE_ID = 'casa'
ROOMS = [('living', 'Phòng khách', 1), ('bed', 'Phòng ngủ', 2),
         ('kitchen', 'Bếp', 3), ('bath', 'Phòng tắm', 4)]

# Keep existing IDs: scenes, schedules, energy and documents reference these IDs.
OVERRIDES = {
    'light-living': ('Đèn phòng khách 1', 'living'),
    'light-balcony': ('Đèn phòng khách 2', 'living'),
    'light-office': ('Đèn phòng khách 4', 'living'),
    'light-bed': ('Đèn phòng ngủ 1', 'bed'),
    'light-bath': ('Đèn trần phòng tắm', 'bath'),
    'curtain': ('Rèm cửa sổ phòng ngủ', 'bed'),
    'cam-balcony': ('Camera cửa kính', 'living'),
    'ac-office': ('Điều hòa khu bàn máy tính', 'living'),
    'plug-office': ('Ổ máy tính', 'living'),
}

# device ID, object name, source reference, binding kind
BINDINGS = [
    ('light-living', 'punto_luz_1', 'game_object:1683541555', 'light'),
    ('light-balcony', 'punto_luz_4', 'game_object:246711313', 'light'),
    ('light-living-3', 'punto_luz_7', 'game_object:485155071', 'light'),
    ('light-office', 'punto_luz_3', 'game_object:1876477424', 'light'),
    ('light-living-5', 'punto_luz_8', 'game_object:2056325552', 'light'),
    ('light-living-6', 'punto_luz_9', 'game_object:442373278', 'light'),
    ('light-living-7', 'punto_luz_10', 'game_object:1004273151', 'light'),
    ('light-living-8', 'punto_luz_11', 'game_object:918458467', 'light'),
    ('light-bed', 'punto_luz_12', 'game_object:980822439', 'light'),
    ('light-bed-2', 'punto_luz_13', 'game_object:922450801', 'light'),
    ('light-kitchen', 'punto_luz_2', 'game_object:2072922615', 'light'),
    ('light-bath', 'punto_luz_5', 'game_object:936903267', 'light'),
    ('light-bath-mirror', 'punto_luz_6', 'game_object:1523471354', 'light'),
    ('curtain', 'persiana_dormitorio', 'game_object:1294729781', 'curtain'),
    ('curtain-bed-roller', 'estor_dormitorio', 'game_object:1803171870', 'curtain'),
    ('curtain-living', 'estor_ventanal', 'game_object:1696505555', 'curtain'),
    ('curtain-kitchen', 'persiana_cocina', 'game_object:1500603428', 'curtain'),
    ('curtain-bath', 'persiana_baño', 'game_object:1386191806', 'curtain'),
    ('cam-entrance', 'camara_ENTRADA', 'prefab_instance:922824021', 'camera'),
    ('cam-balcony', 'camara_VENTANAL', 'prefab_instance:1446704627', 'camera'),
    ('cam-living', 'Camera_SALON', 'prefab_instance:1568793768', 'camera'),
    ('cam-bed', 'Camera_HABITACION', 'prefab_instance:404119791', 'camera'),
    ('cam-kitchen', 'Camera_COCINA', 'prefab_instance:277518556', 'camera'),
    ('cam-tv', 'camara_TV', 'prefab_instance:1715610386', 'camera'),
    ('tv-living', 'TV', 'prefab_instance:2051729301', 'tv'),
    ('speaker-living', 'Speaker', 'prefab_instance:994465538', 'speaker'),
    ('fan-kitchen', 'campana', 'prefab_instance:1705393556', 'fan'),
]


def align_devices(legacy: list[dict]) -> list[Device]:
    raw = deepcopy(legacy)
    for item in raw:
        if item['id'] in OVERRIDES:
            item['name'], item['room'] = OVERRIDES[item['id']]
    by_id = {item['id']: item for item in raw}

    def add(identifier, name, room, template):
        item = deepcopy(by_id[template])
        item.update(id=identifier, name=name, room=room)
        # New models must not inherit a powered-on state from the legacy template.
        if item['kind'] == 'bulb': item['state'] = {'power': False, **({'brightness': 60} if 'brightness' in item['state'] else {})}
        if item['kind'] == 'curtain': item['state'] = {'preset': 'closed', 'position': 0}
        raw.append(item)

    add('light-living-3', 'Đèn phòng khách 3', 'living', 'light-balcony')
    for n in range(5, 9): add(f'light-living-{n}', f'Đèn phòng khách {n}', 'living', 'light-office')
    add('light-bed-2', 'Đèn đầu giường phòng ngủ', 'bed', 'light-bed')
    add('light-bath-mirror', 'Đèn gương phòng tắm', 'bath', 'light-bath')
    for identifier, name, room in [
        ('curtain-bed-roller', 'Rèm cuốn phòng ngủ', 'bed'),
        ('curtain-living', 'Rèm cửa kính phòng khách', 'living'),
        ('curtain-kitchen', 'Rèm cửa sổ bếp', 'kitchen'),
        ('curtain-bath', 'Rèm cửa sổ phòng tắm', 'bath'),
    ]: add(identifier, name, room, 'curtain')
    for identifier, name, room in [
        ('cam-living', 'Camera phòng khách', 'living'), ('cam-bed', 'Camera phòng ngủ', 'bed'),
        ('cam-kitchen', 'Camera bếp', 'kitchen'), ('cam-tv', 'Camera khu TV', 'living'),
    ]: add(identifier, name, room, 'cam-entrance')
    return [Device.model_validate(item) for item in raw]
