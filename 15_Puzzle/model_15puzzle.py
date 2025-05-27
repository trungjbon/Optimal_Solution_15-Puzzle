import gurobipy as gp
from gurobipy import GRB
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def is_solvable(initial_state):
    inversions = 0
    empty_tile_row = 0  # Hàng của ô trống, đánh số từ 1

    for i in range(len(initial_state)):
        if initial_state[i] == 0:  # Tìm vị trí của ô trống
            empty_tile_row = i // 4 + 1  # Tính hàng của ô trống
        else:
            for j in range(i + 1, len(initial_state)):
                if initial_state[j] != 0 and initial_state[i] > initial_state[j]:
                    inversions += 1

    # Kiểm tra xem tổng số đảo ngược và hàng của ô trống có cùng tính chẵn lẻ hay không
    return (inversions % 2 == 0) == (empty_tile_row % 2 == 0)

def model(initial_state):
    initial = []
    for i in range(1, 16):
        initial.append(initial_state.index(i) + 1)
    initial.append(initial_state.index(0) + 1)

    # Khởi tạo mô hình
    model = gp.Model("Tile Puzzle")

    # Tập hợp các tiles và khoảng thời gian
    I = [i for i in range(16)]  # 0 là ô trống
    T = [t for t in range(1, 17)]  # Giả sử có 99 bước di chuyển

    final =   [ 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16]  # Goal positions

    # Biến số
    p = model.addVars(I, T, vtype=GRB.INTEGER, name="p", lb=1, ub=16)
    x = model.addVars(T, vtype=GRB.INTEGER, name="x", lb=1, ub=4)
    y = model.addVars(T, vtype=GRB.INTEGER, name="y", lb=0, ub=3)
    z = model.addVars(I, T, vtype=GRB.BINARY, name="z")
    u = model.addVars(T, vtype=GRB.BINARY, name="u")
    d = model.addVars(T, vtype=GRB.BINARY, name="d")
    l = model.addVars(T, vtype=GRB.BINARY, name="l")
    r = model.addVars(T, vtype=GRB.BINARY, name="r")

    k = model.addVar(vtype=GRB.BINARY, name="k")
    epsilon = 1e-10

    # Ràng buộc
    # Ràng buộc: ô trống chỉ có thể di chuyển một lần trong mỗi bước
    model.addConstrs((u[t] + d[t] + l[t] + r[t] == z[15, t] for t in T), name="BlankMoveOnce")

    # Ràng buộc: cập nhật vị trí của ô trống sau mỗi bước di chuyển va đảm bảo ô trống chỉ di chuyển một ô mỗi lần
    for t in T:
        if t != max(T):
            model.addConstr(p[15, t + 1] == p[15, t] - 4 * u[t] + 4 * d[t] - l[t] + r[t], name="UpdateBlank")

    # Ràng buộc: đảm bảo chỉ các số chỉ đổi số với ô trống, không đổi chỗ với ô khác
    for t in T:
        if t != max(T):
            model.addConstrs((p[i, t + 1] - p[15, t] + 16 * z[i, t] <= 16 for i in I if i != 15), name="TileMoveUp")
            model.addConstrs((p[i, t + 1] - p[15, t] - 16 * z[i, t] >= -16 for i in I if i != 15), name="TileMoveDown")

    # Ràng buộc: xác định tọa độ x và y của ô trống
    model.addConstrs((p[15, t] == x[t] + 4 * y[t] for t in T), name="DefineCoordinates")

    # Ràng buộc: hạn chế di chuyển của ô trống ở cạnh trên
    # model.addConstrs((5 * u[t] <= p[15, t] for t in T), name="TopEdge")
    model.addConstrs((u[t] <= y[t] for t in T), name="TopEdge")

    # Ràng buộc: hạn chế di chuyển của ô trống ở cạnh dưới
    # model.addConstrs((4 * d[t] <= 16 - p[15, t] for t in T), name="BottomEdge")
    model.addConstrs((d[t] <= 3 - y[t] for t in T), name="BottomEdge")

    # Ràng buộc: hạn chế di chuyển của ô trống ở cạnh trái
    model.addConstrs((l[t] <= x[t] - 1 for t in T), name="LeftEdge")

    # Ràng buộc: hạn chế di chuyển của ô trống ở cạnh phải
    model.addConstrs((r[t] <= 4 - x[t] for t in T), name="RightEdge")

    # Ràng buộc: đảm bảo mỗi ô được gán một vị trí tại mỗi thời điểm
    model.addConstrs((gp.quicksum(p[i, t] for i in I) == gp.quicksum(range(1, 17)) for t in T), name="AssignPosition")

    # Ràng buộc: đảm bảo vị trí của các tile khác nhau là khác nhau
    for t in T:
        for i in range(max(I)-1):
            for j in range(i+1, max(I)):
                model.addConstr(k * (p[i, t] - p[j, t]) >= epsilon)


    # Ràng buộc: đảm bảo một trong các ô số di chuyển nếu ô trống di chuyển
    model.addConstrs((z[15, t] == gp.quicksum(z[i, t] for i in I if i != 15) for t in T), name="NumberedTileMoves")

    # Ràng buộc: không thể đổi chỗ với ô trống ở các phía chéo, hoặc ô trống chỉ có thể lên, xuống, trái, phải
    for t in T:
        if t != max(T):
            model.addConstrs((p[i, t] - p[i, t + 1] + 4 * z[i, t] >= 0 for i in I), name="MaintainPositionUp")
            model.addConstrs((p[i, t] - p[i, t + 1] - 4 * z[i, t] <= 0 for i in I), name="MaintainPositionDown")


    # Ràng buộc: vị trí ban đầu
    model.addConstrs((p[i, 1] == initial[i] for i in I), name="InitialPositions")

    # Ràng buộc: vị trí cuối cùng
    model.addConstrs((p[i, max(T)] == final[i] for i in I), name="FinalPositions")

    # Hàm mục tiêu: Minimize tổng số bước di chuyển của ô trống
    model.setObjective(gp.quicksum(z[15, t] for t in T), GRB.MINIMIZE)

    # Giải mô hình
    # model.setParam('MIPFocus', 1)  # Focus on finding feasible solutions
    # model.setParam('SolutionLimit', 1)  # Stop after finding one feasible solution
    # model.setParam('TimeLimit', 120)
    # Solver time limit of 60 seconds

    model.optimize()

    if model.status != GRB.INFEASIBLE:
        print("Optimal solution found:")
        print(f"Value optimal: {model.objVal}")

        list_solutions = []
        # In trạng thái của bảng tại mỗi bước
        previous_board = None
        step = 0
        for t in T:
            board = [[0 for _ in range(4)] for _ in range(4)]
            for i in I:
                pos = int(p[i, t].x)
                row = (pos - 1) // 4
                col = (pos - 1) % 4
                board[row][col] = i + 1 if i != 15 else 0
            
            if board != previous_board:
                list_solutions.append(board)
                print(f"Step {step}:")
                for row in board:
                    print(' '.join(str(num).rjust(2) for num in row))
                print("\n")
                step = step + 1
            
            previous_board = board
        return list_solutions
    else:
        print("No solution found")
        return None

def visualize_solution(list_solutions):

    # Define the function to plot a single puzzle state with an enhanced 3D effect
    def plot_puzzle_state(state, ax):
        ax.clear()
        for i in range(4):
            for j in range(4):
                value = state[i][j]
                if value == 0:
                    color = 'white'
                    text = ""
                else:
                    color = '#4682B4'  # Darker blue color for the tiles
                    text = str(value)
                # Draw the main tile with gaps between tiles
                ax.add_patch(plt.Rectangle((j + 0.05, 3 - i + 0.05), 0.9, 0.9, fill=True, color=color, edgecolor='black', linewidth=2))
                # Add the 3D effect by adding a gradient
                # Top side (lighter shade)
                ax.add_patch(plt.Polygon(((j + 0.05, 3 - i + 0.95), (j + 0.1, 3 - i + 1), (j + 0.95, 3 - i + 0.1), (j + 1, 3 - i + 0.05)), closed=True, color='#5A9BD4'))
                # Left side (darker shade)
                ax.add_patch(plt.Polygon(((j + 0.05, 3 - i + 0.05), (j + 0.05, 3 - i + 0.95), (j + 0.1, 3 - i + 1), (j + 0.1, 3 - i + 0.1)), closed=True, color='#2F4F6F'))
                # Add the text in the middle of the tile
                ax.text(j + 0.5, 3 - i + 0.5, text, ha='center', va='center', fontsize=20, color='white')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect('equal', adjustable='box')

    # Create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(6, 6))

    # Define the update function for the animation
    def update(frame):
        plot_puzzle_state(list_solutions[frame], ax)

    # Create the animation
    ani = FuncAnimation(fig, update, frames=len(list_solutions), repeat=False, interval=1300)

    # Show the animation
    plt.show()


def excuted(initial_state):
    if is_solvable(initial_state):
        print("Bài toán có thể giải được\n")
        list_solutions = model(initial_state)
        if list_solutions != None:
            visualize_solution(list_solutions)
    else:
        print("Bài toán không thể giải được")

initial_state1 = [5, 1, 2, 4, 0, 7, 3, 8, 9, 14, 10, 11, 6, 13, 15, 12] # 15 steps
initial_state2 = [5, 1, 2, 3, 9, 6, 7, 4, 13, 10, 11, 8, 14, 15, 0, 12] # 11 steps
excuted(initial_state1)
