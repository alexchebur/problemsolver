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
        
        exit_pos = random.choice(empty_cells)
        map_data[exit_pos[0]][exit_pos[1]] = Tile.EXIT
        empty_cells.remove(exit_pos)
        
        # Добавляем случайных врагов и предметы
        for _ in range(min(5, len(empty_cells))):
            pos = random.choice(empty_cells)
            map_data[pos[0]][pos[1]] = random.choice([Tile.ENEMY, Tile.ITEM])
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
            map_data[y][x] = Tile.FLOOR
            map_data[new_y][new_x] = Tile.PLAYER
            return (new_y, new_x)
    return player_pos

def check_quest_progress(map_data, player_pos, quest):
    y, x = player_pos
    current_tile = map_data[y][x]
    
    if quest["type"] == QuestType.KILL and current_tile == Tile.ENEMY:
        quest["completed"] = True
        map_data[y][x] = Tile.FLOOR
        return "Вы убили врага и выполнили задание!"
    
    elif quest["type"] == QuestType.COLLECT and current_tile == Tile.ITEM:
        quest["completed"] = True
        map_data[y][x] = Tile.FLOOR
        return "Вы нашли предмет и выполнили задание!"
    
    elif current_tile == Tile.EXIT:
        if quest["completed"]:
            return "Поздравляем! Вы выполнили задание и нашли выход!"
        else:
            return "Выход найден, но задание не выполнено!"
    
    return None

def main():
    st.title("Roguelike Игра")
    
    if "map" not in st.session_state:
        st.session_state.map, st.session_state.player_pos = create_map(20, 10)
        st.session_state.quest = generate_quest()
        st.session_state.message = "Добро пожаловать в подземелье!"
    
    # Отображение карты
    map_display = "\n".join("".join(tile.value for tile in row) for row in st.session_state.map)
    st.text_area("Карта", map_display, height=300)
    
    # Отображение задания
    quest = st.session_state.quest
    st.subheader("Текущее задание:")
    st.write(f"{quest['type'].value} {quest['target']}")
    
    if quest["completed"]:
        st.success("Задание выполнено! Найдите выход (X).")
    
    # Управление
    st.subheader("Управление")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("↑ Вверх"):
            st.session_state.player_pos = move_player(st.session_state.map, st.session_state.player_pos, Direction.UP)
    
    with col2:
        if st.button("← Лево"):
            st.session_state.player_pos = move_player(st.session_state.map, st.session_state.player_pos, Direction.LEFT)
        if st.button("→ Право"):
            st.session_state.player_pos = move_player(st.session_state.map, st.session_state.player_pos, Direction.RIGHT)
    
    with col3:
        if st.button("↓ Вниз"):
            st.session_state.player_pos = move_player(st.session_state.map, st.session_state.player_pos, Direction.DOWN)
    
    # Проверка прогресса
    message = check_quest_progress(
        st.session_state.map,
        st.session_state.player_pos,
        st.session_state.quest
    )
    
    if message:
        st.session_state.message = message
    
    st.info(st.session_state.message)
    
    # Новая игра
    if st.button("Новая игра"):
        st.session_state.map, st.session_state.player_pos = create_map(20, 10)
        st.session_state.quest = generate_quest()
        st.session_state.message = "Добро пожаловать в подземелье!"
        st.rerun()

if __name__ == "__main__":
    main()
