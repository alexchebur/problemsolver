import streamlit as st
import random
import numpy as np
from enum import Enum

class Tile(Enum):
    WALL = '#'
    FLOOR = '.'
    PLAYER = '@'
    ENEMY = 'E'
    ITEM = '!'
    EXIT = 'X'

class QuestType(Enum):
    KILL = "Убить"
    COLLECT = "Найти"

class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

def generate_cave(width, height, fill_prob=0.4):
    grid = np.random.choice([0, 1], size=(height, width), p=[1-fill_prob, fill_prob])
    
    for _ in range(5):
        new_grid = grid.copy()
        for y in range(height):
            for x in range(width):
                neighbors = np.sum(grid[max(0, y-1):min(height, y+2), max(0, x-1):min(width, x+2)]) - grid[y, x]
                if grid[y, x] == 1:
                    new_grid[y, x] = 1 if neighbors >= 3 else 0
                else:
                    new_grid[y, x] = 1 if neighbors >= 5 else 0
        grid = new_grid
    
    return grid

def create_map(width, height):
    cave = generate_cave(width, height)
    map_data = []
    
    for row in cave:
        map_row = []
        for cell in row:
            map_row.append(Tile.WALL if cell == 1 else Tile.FLOOR)
        map_data.append(map_row)
    
    # Добавляем игрока, выход и случайные объекты
    empty_cells = [(y, x) for y in range(height) for x in range(width) if map_data[y][x] == Tile.FLOOR]
    
    if empty_cells:
        player_pos = random.choice(empty_cells)
        map_data[player_pos[0]][player_pos[1]] = Tile.PLAYER
        empty_cells.remove(player_pos)
        
        # Добавляем выход
        if empty_cells:
            exit_pos = random.choice(empty_cells)
            map_data[exit_pos[0]][exit_pos[1]] = Tile.EXIT
            empty_cells.remove(exit_pos)
        
        # Добавляем случайных врагов и предметы
        num_entities = min(5, len(empty_cells) // 2)
        for _ in range(num_entities):
            if empty_cells:
                pos = random.choice(empty_cells)
                map_data[pos[0]][pos[1]] = Tile.ENEMY
                empty_cells.remove(pos)
            
            if empty_cells:
                pos = random.choice(empty_cells)
                map_data[pos[0]][pos[1]] = Tile.ITEM
                empty_cells.remove(pos)
    
    return map_data, player_pos

def generate_quest():
    quest_type = random.choice(list(QuestType))
    target = random.choice(["Гоблина", "Дракона", "Скелета", "Волшебника"] if quest_type == QuestType.KILL else
                          ["магический меч", "древний свиток", "эликсир здоровья", "золотой ключ"])
    return {
        "type": quest_type,
        "target": target,
        "completed": False
    }

def move_player(map_data, player_pos, direction):
    y, x = player_pos
    dy, dx = direction.value
    new_y, new_x = y + dy, x + dx
    
    if 0 <= new_y < len(map_data) and 0 <= new_x < len(map_data[0]):
        if map_data[new_y][new_x] in [Tile.FLOOR, Tile.ENEMY, Tile.ITEM, Tile.EXIT]:
            # Сохраняем тип тайла, на который переходим (для проверки квеста)
            target_tile = map_data[new_y][new_x]
            
            # Перемещаем игрока
            map_data[y][x] = Tile.FLOOR
            map_data[new_y][new_x] = Tile.PLAYER
            
            return (new_y, new_x), target_tile
    return player_pos, None

def check_quest_progress(quest, target_tile):
    if target_tile is None:
        return None
        
    if quest["type"] == QuestType.KILL and target_tile == Tile.ENEMY:
        quest["completed"] = True
        return f"Вы убили врага! Задание выполнено!"
    
    elif quest["type"] == QuestType.COLLECT and target_tile == Tile.ITEM:
        quest["completed"] = True
        return f"Вы нашли предмет! Задание выполнено!"
    
    elif target_tile == Tile.EXIT:
        if quest["completed"]:
            return "Поздравляем! Вы выполнили задание и нашли выход!"
        else:
            return "Выход найден, но задание не выполнено!"
    
    return None

def render_map(map_data):
    return "\n".join("".join(tile.value for tile in row) for row in map_data)

def main():
    st.title("🗡️ Roguelike Игра")
    
    # Инициализация состояния игры
    if "game_initialized" not in st.session_state:
        st.session_state.map, st.session_state.player_pos = create_map(20, 10)
        st.session_state.quest = generate_quest()
        st.session_state.message = "Добро пожаловать в подземелье! Используйте кнопки для перемещения."
        st.session_state.game_initialized = True
        st.session_state.game_over = False
    
    # Отображение карты
    st.subheader("Карта подземелья")
    map_display = render_map(st.session_state.map)
    st.text_area("", map_display, height=300, key="map_display")
    
    # Отображение задания
    st.subheader("📜 Задание")
    quest = st.session_state.quest
    quest_text = f"{quest['type'].value} {quest['target']}"
    
    if quest["completed"]:
        st.success(f"✅ {quest_text} - ВЫПОЛНЕНО!")
        st.info("Найдите выход (X) чтобы завершить игру!")
    else:
        st.warning(f"🎯 {quest_text}")
    
    # Легенда
    st.subheader("📖 Легенда")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.text("@ - Игрок")
    with col2:
        st.text("# - Стена")
    with col3:
        st.text(". - Пол")
    with col4:
        st.text("E - Враг")
    with col5:
        st.text("! - Предмет")
    
    # Управление
    st.subheader("🎮 Управление")
    
    # Верхний ряд кнопок
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("↑ Вверх", key="up", use_container_width=True):
            if not st.session_state.game_over:
                new_pos, target_tile = move_player(st.session_state.map, st.session_state.player_pos, Direction.UP)
                st.session_state.player_pos = new_pos
                
                message = check_quest_progress(st.session_state.quest, target_tile)
                if message:
                    st.session_state.message = message
                    if target_tile == Tile.EXIT and st.session_state.quest["completed"]:
                        st.session_state.game_over = True
    
    # Средний ряд кнопок
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Лево", key="left", use_container_width=True):
            if not st.session_state.game_over:
                new_pos, target_tile = move_player(st.session_state.map, st.session_state.player_pos, Direction.LEFT)
                st.session_state.player_pos = new_pos
                
                message = check_quest_progress(st.session_state.quest, target_tile)
                if message:
                    st.session_state.message = message
                    if target_tile == Tile.EXIT and st.session_state.quest["completed"]:
                        st.session_state.game_over = True
    
    with col3:
        if st.button("→ Право", key="right", use_container_width=True):
            if not st.session_state.game_over:
                new_pos, target_tile = move_player(st.session_state.map, st.session_state.player_pos, Direction.RIGHT)
                st.session_state.player_pos = new_pos
                
                message = check_quest_progress(st.session_state.quest, target_tile)
                if message:
                    st.session_state.message = message
                    if target_tile == Tile.EXIT and st.session_state.quest["completed"]:
                        st.session_state.game_over = True
    
    # Нижний ряд кнопок
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("↓ Вниз", key="down", use_container_width=True):
            if not st.session_state.game_over:
                new_pos, target_tile = move_player(st.session_state.map, st.session_state.player_pos, Direction.DOWN)
                st.session_state.player_pos = new_pos
                
                message = check_quest_progress(st.session_state.quest, target_tile)
                if message:
                    st.session_state.message = message
                    if target_tile == Tile.EXIT and st.session_state.quest["completed"]:
                        st.session_state.game_over = True
    
    # Сообщения
    st.subheader("📢 События")
    if st.session_state.game_over:
        st.balloons()
        st.success(st.session_state.message)
        st.success("🎉 Игра завершена! Начните новую игру.")
    else:
        st.info(st.session_state.message)
    
    # Управление игрой
    st.subheader("⚙️ Управление игрой")
    if st.button("🔄 Новая игра"):
        st.session_state.map, st.session_state.player_pos = create_map(20, 10)
        st.session_state.quest = generate_quest()
        st.session_state.message = "Новая игра началась! Используйте кнопки для перемещения."
        st.session_state.game_over = False
        st.rerun()
    
    if st.button("🔍 Обновить отображение"):
        st.rerun()

if __name__ == "__main__":
    main()
