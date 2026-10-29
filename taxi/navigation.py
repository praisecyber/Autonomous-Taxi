import heapq

# --- 2D OCCUPANCY GRID (The Virtual Map) ---
# 0 = Free drivable space
# 1 = Solid obstacle (Walls, curbs, restricted areas)
CAMPUS_GRID = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 0, 1, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]

# Map our destinations to exact [Row, Column] coordinates on the grid
LOCATIONS = {
    "STOP_A": {"name": "Engineering", "r": 0, "c": 0},
    "STOP_B": {"name": "Library", "r": 0, "c": 9},
    "STOP_C": {"name": "Student Centre", "r": 6, "c": 4}
}

def heuristic(a, b):
    """Calculates Manhattan distance between two points on the grid."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_grid(start, goal, grid):
    """Calculates the shortest path avoiding 1s (obstacles)."""
    rows, cols = len(grid), len(grid[0])
    
    # queue stores: (priority_score, distance_traveled, current_coordinate, path_history)
    queue = [(0, 0, start, [start])]
    visited = set()
    
    while queue:
        _, cost, current, path = heapq.heappop(queue)
        
        if current == goal:
            return path, cost
            
        if current in visited:
            continue
        visited.add(current)
        
        r, c = current
        # Directions: Up, Down, Left, Right
        neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        
        for nr, nc in neighbors:
            # Check if neighbor is inside grid and is not a wall (0)
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                if (nr, nc) not in visited:
                    new_cost = cost + 1
                    priority = new_cost + heuristic((nr, nc), goal)
                    heapq.heappush(queue, (priority, new_cost, (nr, nc), path + [(nr, nc)]))
                    
    return None, float('inf')

def find_shortest_path(start_id, destination_id):
    """Adapter function for the MissionSupervisor to call."""
    start = LOCATIONS.get(start_id)
    goal = LOCATIONS.get(destination_id)
    
    if not start or not goal:
        return None, float('inf')
        
    start_coords = (start["r"], start["c"])
    goal_coords = (goal["r"], goal["c"])
    
    path, cost = a_star_grid(start_coords, goal_coords, CAMPUS_GRID)
    
    if path:
        # Convert coordinate tuples to string format for the API response
        string_path = [f"[{r},{c}]" for r, c in path]
        return string_path, cost
    return None, float('inf')

def print_map_with_path(path):
    """Visualizes the map and the chosen route in the terminal."""
    print("\n--- CAMPUS ROUTE VISUALIZER ---")
    for r in range(len(CAMPUS_GRID)):
        row_str = ""
        for c in range(len(CAMPUS_GRID[0])):
            if (r, c) == path[0]:
                row_str += " A " # Start
            elif (r, c) == path[-1]:
                row_str += " B " # Destination
            elif (r, c) in path:
                row_str += " • " # Path taken
            elif CAMPUS_GRID[r][c] == 1:
                row_str += "███" # Wall/Obstacle
            else:
                row_str += "   " # Free space
        print(row_str)
    print("-------------------------------\n")

import re

def update_grid(coord_str, is_blocked):
    """Places or removes a temporary wall on the grid."""
    match = re.match(r"\[(\d+),(\d+)\]", coord_str)
    if match:
        r, c = int(match.group(1)), int(match.group(2))
        CAMPUS_GRID[r][c] = 1 if is_blocked else 0

def find_path_from_coordinate(start_coord_str, destination_id):
    """Recalculates the A* route from a live string coordinate."""
    match = re.match(r"\[(\d+),(\d+)\]", start_coord_str)
    goal = LOCATIONS.get(destination_id)
    
    if not match or not goal:
        return None, float('inf')
        
    start_coords = (int(match.group(1)), int(match.group(2)))
    goal_coords = (goal["r"], goal["c"])
    
    path, cost = a_star_grid(start_coords, goal_coords, CAMPUS_GRID)
    
    if path:
        return [f"[{r},{c}]" for r, c in path], cost
    return None, float('inf')

if __name__ == "__main__":
    # Test the grid algorithm: Engineering (0,0) to Student Centre (6,4)
    start_node = "STOP_A"
    dest_node = "STOP_C"
    
    start_info = LOCATIONS[start_node]
    dest_info = LOCATIONS[dest_node]
    
    print(f"Request: {start_info['name']} -> {dest_info['name']}")
    
    # Run A* Pathfinding
    raw_path, total_distance = a_star_grid(
        (start_info["r"], start_info["c"]), 
        (dest_info["r"], dest_info["c"]), 
        CAMPUS_GRID
    )
    
    if raw_path:
        print_map_with_path(raw_path)
        print(f"Total distance: {total_distance} grid units")
    else:
        print("Error: No valid path exists.")