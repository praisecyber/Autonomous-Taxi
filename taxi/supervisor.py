import time
import threading
from taxi.navigation import find_shortest_path, update_grid, find_path_from_coordinate

class MissionSupervisor:
    def __init__(self):
        self.state = "READY"
        self.current_route = []
        self.current_position = None
        self.destination_id = None
        self.total_distance = 0.0
        self.fault_reason = ""
        self.blocked_cell = None

    def book_trip(self, start_id, destination_id):
        if self.state not in ["READY", "COMPLETED"]:
            return {"success": False, "error": f"Taxi is currently {self.state}"}
        
        route, distance = find_shortest_path(start_id, destination_id)
        if route:
            self.current_route = route
            self.current_position = route[0]
            self.destination_id = destination_id
            self.total_distance = distance
            self.state = "ACTIVE"
            self.fault_reason = ""
            threading.Thread(target=self._simulate_movement, daemon=True).start()
            return {"success": True, "route": route, "distance": distance}
        
        return {"success": False, "error": "No valid path"}

    def _simulate_movement(self):
        while self.current_position != self.current_route[-1]:
            while self.state == "PAUSED":
                time.sleep(0.5) 
                
            if self.state == "FAULT":
                break
            
            # Find our current index and move to the next step in the route array
            current_idx = self.current_route.index(self.current_position)
            if current_idx + 1 < len(self.current_route):
                self.current_position = self.current_route[current_idx + 1]
                time.sleep(1.5)
            else:
                break
            
        if self.state == "ACTIVE":
            self.state = "COMPLETED"
            print("Destination Reached!")

    def trigger_pause(self, reason):
        if self.state == "ACTIVE":
            print(f"HAZARD DETECTED: {reason}. Attempting to reroute...")
            
            # 1. Identify the cell directly in front of the taxi
            try:
                current_idx = self.current_route.index(self.current_position)
                self.blocked_cell = self.current_route[current_idx + 1]
            except (ValueError, IndexError):
                self.state = "PAUSED"
                self.fault_reason = reason
                return
                
            # 2. Tell the map this cell is now a temporary wall
            update_grid(self.blocked_cell, is_blocked=True)
            
            # 3. Recalculate A* from current position avoiding the new wall
            new_route, distance = find_path_from_coordinate(self.current_position, self.destination_id)
            
            if new_route:
                print("REROUTE SUCCESSFUL. Changing lanes to avoid obstacle.")
                self.current_route = new_route
                # Remove the temporary wall from the grid after calculation so it doesn't break future trips
                update_grid(self.blocked_cell, is_blocked=False) 
            else:
                print("NO ALTERNATIVE ROUTE. Road is blocked on all sides. Waiting for traffic.")
                self.state = "PAUSED"
                self.fault_reason = reason

    def resume_movement(self):
        if self.state == "PAUSED":
            if self.blocked_cell:
                update_grid(self.blocked_cell, is_blocked=False)
            self.state = "ACTIVE"
            self.fault_reason = ""
            print("PATH CLEAR: Resuming movement.")