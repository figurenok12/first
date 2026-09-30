# Редактор базы RimWorld (для Claude)

Быстрый способ: `rw.py` правит уже готовый сейв короткими командами (вывод крошечный).

    python3 rw.py -c "show 114 107 160 157; put Bed 120 140 0; wall 115 140 130 140; door 120 140; save"

Команды: show, info, put, wall, box, door, rm, mv, rot, floor, roof, wire, autowire, hp, zone, save
(полный список: `python3 rw.py`). Новые здания клонируются из уже существующих на карте, получают
полное здоровье и автоматически подключаются к проводам.

Полная пересборка всей базы из плана (тяжёлый путь): правим `layout.py`, затем
`render.py` → `check.py` → `apply_world.py` → `validate.py`.
Нужен Pillow (`pip install pillow`). Проверено только по файлу сейва, не в игре.
