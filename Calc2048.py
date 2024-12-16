import pygame
import sys
import random
import math
import matplotlib.pyplot as plt
import io
import numpy as np

# 初始化Pygame
pygame.init()

# 定义常量
GRID_SIZE = 4
TILE_SIZE = 100
TILE_PADDING = 10
WINDOW_SIZE = GRID_SIZE * (TILE_SIZE + TILE_PADDING) + TILE_PADDING
FPS = 60

# 定义颜色
BACKGROUND_COLOR = (187, 173, 160)
EMPTY_TILE_COLOR = (205, 193, 180)
TILE_COLORS = {
    "integral": (238, 228, 218),
    "derivative": (237, 224, 200),
    "e^x": (242, 177, 121)
}
TEXT_COLOR = (119, 110, 101)
FONT = pygame.font.SysFont("Arial", 40, bold=True)
SMALL_FONT = pygame.font.SysFont("Arial", 20, bold=True)

# 设置屏幕
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE + 100))  # 增加空间显示分数与信息
pygame.display.set_caption("Calc2048")

# 设置时钟
clock = pygame.time.Clock()

def render_latex(latex, fontsize=24, color='black'):
    """使用Matplotlib渲染LaTeX表达式，并转换为Pygame表面"""
    plt.rc('text', usetex=True)
    plt.rc('font', size=fontsize)

    fig = plt.figure(figsize=(0.01, 0.01))  # 尺寸会被调整
    text = plt.text(0, 0, f"${latex}$", color=color)

    # 去除边框和空白
    plt.axis('off')
    buffer = io.BytesIO()
    try:
        plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0.1, transparent=True)
    except RuntimeError as e:
        print(f"Error rendering LaTeX: {e}")
        plt.close(fig)
        return None
    plt.close(fig)
    buffer.seek(0)
    try:
        image = pygame.image.load(io.BytesIO(buffer.read())).convert_alpha()
    except pygame.error as e:
        print(f"Pygame failed to load image: {e}")
        return None
    
    return image

class Tile:
    def __init__(self):
        # 父类Tile在本例中不存储特定数据，仅作为继承用
        self.image = None  # 将存储渲染后的图像

    def show(self, surface, x, y):
        if self.image:
            rect = self.image.get_rect(center=(x + TILE_SIZE / 2, y + TILE_SIZE / 2))
            surface.blit(self.image, rect)

class CalculusTile(Tile):
    def __init__(self, value):
        super().__init__()
        self.value = value
        # 根据value决定展示的LaTeX表达式
        if value == 0:
            latex = r"C"
        elif value > 0:
            # 正数代表积分次数
            latex = r"\int^{%d} dx^{%d}" % (self.value, self.value)
        else:
            # 负数代表微分次数
            latex = r"d^{%d}/dx^{%d}" % (abs(self.value), abs(self.value))
        
        # 选择颜色
        if self.value > 0:
            color = TILE_COLORS["integral"]
        else:
            color = TILE_COLORS["derivative"]
        
        # 渲染LaTeX表达式
        self.image = render_latex(latex, fontsize=24, color='black')
        if self.image:
            # 调整图像大小以适应TILE_SIZE
            self.image = pygame.transform.scale(self.image, (TILE_SIZE - 20, TILE_SIZE - 20))

class ExpTile(Tile):
    def __init__(self, numerator, denominator, power):
        super().__init__()
        gcd_value = gcd(numerator, denominator)
        numerator //= gcd_value
        denominator //= gcd_value

        self.numerator = numerator
        self.denominator = denominator
        self.power = power

        # 显示LaTeX表达式: "n/d \cdot e^{px}"
        if self.denominator == 1:
            fraction = f"{self.numerator}"
        else:
            fraction = f"\\frac{{{self.numerator}}}{{{self.denominator}}}"
        if self.power == 0:
            latex = r"%s \cdot e^{0}" % fraction
        elif self.power == 1:
            latex = r"%s \cdot e^{x}" % fraction
        else:
            latex = r"%s \cdot e^{%dx}" % (fraction, self.power)

        # 选择颜色
        color = TILE_COLORS["e^x"]

        # 渲染LaTeX表达式
        self.image = render_latex(latex, fontsize=24, color='black')
        if self.image:
            # 调整图像大小以适应TILE_SIZE
            self.image = pygame.transform.scale(self.image, (TILE_SIZE - 20, TILE_SIZE - 20))

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def initialize_grid():
    """初始化网格，并随机添加两个方块"""
    grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    add_new_tile(grid)
    add_new_tile(grid)
    return grid

def add_new_tile(grid):
    """在空白位置随机添加一个新的方块，ExpTile或CalculusTile"""
    empty_cells = [(i, j) for i in range(GRID_SIZE) for j in range(GRID_SIZE) if grid[i][j] == 0]
    if not empty_cells:
        return
    i, j = random.choice(empty_cells)
    # 更高概率生成CalculusTile
    TileClass = random.choices([ExpTile, CalculusTile], weights=[2, 8])[0]
    if TileClass == ExpTile:
        # 生成一个e^x类型的tile，需要numerator, denominator, power随机
        numerator = random.randint(1, 5)
        denominator = random.randint(1, 5)
        power = random.randint(1, 2)
        grid[i][j] = ExpTile(numerator, denominator, power)
    else:
        # 生成CalculusTile，随机value
        value = random.randint(-2, 2)  # 包括-2, -1, 0, 1, 2
        grid[i][j] = CalculusTile(value)

def compress(grid):
    """压缩网格，将所有非零方块向左移动"""
    new_grid = []
    changed = False
    for row in grid:
        new_row = [num for num in row if num != 0]
        new_row += [0] * (GRID_SIZE - len(new_row))
        if new_row != row:
            changed = True
        new_grid.append(new_row)
    return new_grid, changed

def merge(grid):
    """合并相邻相同类型的方块"""
    changed = False
    for row in grid:
        for i in range(GRID_SIZE - 1):
            left_tile = row[i]
            right_tile = row[i+1]
            if left_tile != 0 and right_tile != 0:
                # 判断类型
                if isinstance(left_tile, CalculusTile) and isinstance(right_tile, CalculusTile):
                    # 合并：相加value
                    merged_tile = CalculusTile(left_tile.value + right_tile.value)
                    row[i] = merged_tile
                    row[i + 1] = 0
                    changed = True
                elif isinstance(left_tile, ExpTile) and isinstance(right_tile, ExpTile):
                    # 合并：分数相乘，指数相加
                    new_num = left_tile.numerator * right_tile.numerator
                    new_den = left_tile.denominator * right_tile.denominator
                    new_pow = left_tile.power + right_tile.power
                    merged_tile = ExpTile(new_num, new_den, new_pow)
                    row[i] = merged_tile
                    row[i + 1] = 0
                    changed = True
                elif (isinstance(left_tile, CalculusTile) and isinstance(right_tile, ExpTile)) or \
                     (isinstance(left_tile, ExpTile) and isinstance(right_tile, CalculusTile)):
                    # 混合合并
                    if isinstance(left_tile, CalculusTile):
                        calc_tile = left_tile
                        exp_tile = right_tile
                        merge_pos = i
                    else:
                        calc_tile = right_tile
                        exp_tile = left_tile
                        merge_pos = i  # 保持合并后的Tile在左侧

                    v = calc_tile.value
                    n = exp_tile.numerator
                    d = exp_tile.denominator
                    p = exp_tile.power

                    if v == 0:
                        merged_tile = ExpTile(n, d, p)
                    elif v > 0:
                        merged_tile = ExpTile(n, d * (p ** v), p)
                    else:
                        merged_tile = ExpTile(n * (p ** -v), d, p)
                    
                    row[merge_pos] = merged_tile
                    row[i + 1] = 0
                    changed = True
    return grid, changed

def reverse(grid):
    """反转每一行"""
    return [row[::-1] for row in grid]

def transpose(grid):
    """转置网格"""
    return [list(row) for row in zip(*grid)]

def move_left(grid):
    """向左移动并合并方块"""
    grid, changed1 = compress(grid)
    grid, changed2 = merge(grid)
    changed = changed1 or changed2
    grid, _ = compress(grid)
    return grid, changed

def move_right(grid):
    """向右移动并合并方块"""
    grid = reverse(grid)
    grid, changed = move_left(grid)
    grid = reverse(grid)
    return grid, changed

def move_up(grid):
    """向上移动并合并方块"""
    grid = transpose(grid)
    grid, changed = move_left(grid)
    grid = transpose(grid)
    return grid, changed

def move_down(grid):
    """向下移动并合并方块"""
    grid = transpose(grid)
    grid, changed = move_right(grid)
    grid = transpose(grid)
    return grid, changed

def can_move(grid):
    """检查是否还有可移动或可合并的方块
    当前规则下几乎永远可以移动，但保留此函数以备将来规则改变"""
    return True

def check_win(grid):
    """检查是否有大于等于2048的方块
    对于ExpTile，我们检查 n/d * e^(p) >= 2^64
    对于CalculusTile暂不进行复杂判断
    """
    max_tile = 0
    for row in grid:
        for tile in row:
            if isinstance(tile, ExpTile):
                try:
                    value = (tile.numerator / tile.denominator) * (math.e ** tile.power)
                    max_tile = max(max_tile, value)
                    if value >= 2 ** 64:
                        return True
                except OverflowError:
                    print("e^x value too large")
                    # 处理指数过大的情况
                    return True
    print(f"Max tile value: {round(max_tile)}")
    return False

def show_text():
    """显示文本，如提示信息"""
    # 在界面底部100像素区域中显示游戏提示
    info_text = "Use arrow to move, Q to exit"
    # 使用Pygame的字体渲染
    text_surface = SMALL_FONT.render(info_text, True, TEXT_COLOR)
    text_rect = text_surface.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE + 50))
    screen.blit(text_surface, text_rect)

def draw_grid(grid):
    """绘制网格、方块和文本"""
    # 先绘制背景
    pygame.draw.rect(screen, BACKGROUND_COLOR, (0, 0, WINDOW_SIZE, WINDOW_SIZE))
    # 绘制空白块或有tile的块
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            x = TILE_PADDING + j * (TILE_SIZE + TILE_PADDING)
            y = TILE_PADDING + i * (TILE_SIZE + TILE_PADDING)
            if grid[i][j] == 0:
                # 空白
                pygame.draw.rect(screen, EMPTY_TILE_COLOR, (x, y, TILE_SIZE, TILE_SIZE), border_radius=8)
            else:
                # 显示方块
                grid[i][j].show(screen, x, y)
    
    # 绘制网格线（可选）
    for i in range(GRID_SIZE + 1):
        # 垂直线
        pygame.draw.line(screen, BACKGROUND_COLOR, 
                         (TILE_PADDING + i * (TILE_SIZE + TILE_PADDING) - TILE_PADDING, TILE_PADDING),
                         (TILE_PADDING + i * (TILE_SIZE + TILE_PADDING) - TILE_PADDING, WINDOW_SIZE - TILE_PADDING),
                        5)
        # 水平线
        pygame.draw.line(screen, BACKGROUND_COLOR, 
                         (TILE_PADDING, TILE_PADDING + i * (TILE_SIZE + TILE_PADDING) - TILE_PADDING),
                         (WINDOW_SIZE - TILE_PADDING, TILE_PADDING + i * (TILE_SIZE + TILE_PADDING) - TILE_PADDING),
                        5)

def main():
    """主函数"""
    grid = initialize_grid()

    while True:
        moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_LEFT:
                    grid, moved = move_left(grid)
                elif event.key == pygame.K_RIGHT:
                    grid, moved = move_right(grid)
                elif event.key == pygame.K_UP:
                    grid, moved = move_up(grid)
                elif event.key == pygame.K_DOWN:
                    grid, moved = move_down(grid)

        if moved:
            add_new_tile(grid)

        if check_win(grid):
            # 简单处理胜利画面
            screen.fill(BACKGROUND_COLOR)
            win_text = "You Win!"
            # 使用LaTeX渲染胜利文本
            win_image = render_latex(win_text, fontsize=40, color='green')
            if win_image:
                win_image = pygame.transform.scale(win_image, (200, 80))
                win_rect = win_image.get_rect(center=(WINDOW_SIZE / 2, WINDOW_SIZE / 2))
                screen.blit(win_image, win_rect)
            else:
                # 如果LaTeX渲染失败，使用Pygame字体渲染
                fallback_surface = FONT.render(win_text, True, (0, 255, 0))
                fallback_rect = fallback_surface.get_rect(center=(WINDOW_SIZE / 2, WINDOW_SIZE / 2))
                screen.blit(fallback_surface, fallback_rect)
            pygame.display.flip()
            pygame.time.wait(3000)
            pygame.quit()
            sys.exit()

        screen.fill(BACKGROUND_COLOR)
        draw_grid(grid)
        show_text()
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
