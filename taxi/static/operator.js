async function issueStop() {
    try {
        const response = await fetch('/api/operator/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'stop', operator_id: 'local_admin' })
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('trip-id').textContent = data.trip_id;
            document.getElementById('trip-state').textContent = data.state;
            document.getElementById('trip-speed').textContent = data.current_speed;
            
            const faultDisplay = document.getElementById('fault-display');
            faultDisplay.style.display = 'block';
            faultDisplay.textContent = `Fault: ${data.fault_reason}`;
        }
    } catch (error) {
        console.error("Failed to communicate with supervisor:", error);
    }
}

async function issueRearm() {
    try {
        const response = await fetch('/api/operator/rearm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'rearm', operator_id: 'local_admin' })
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('trip-id').textContent = data.trip_id;
            document.getElementById('trip-state').textContent = data.state;
            document.getElementById('trip-speed').textContent = data.current_speed;
            
            const faultDisplay = document.getElementById('fault-display');
            faultDisplay.style.display = 'none';
            faultDisplay.textContent = '';
        }
    } catch (error) {
        console.error("Failed to communicate with supervisor:", error);
    }
}

const ws = new WebSocket(`ws://${window.location.host}/api/operator/ws/telemetry`);

// Add this new function to start the trip
async function startSimulation() {
    try {
        await fetch('/api/operator/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: 'Engineering', destination: 'Library' })
        });
    } catch (error) {
        console.error("Failed to start mission:", error);
    }
}

// Update your existing ws.onmessage function to include distance:
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    document.getElementById('trip-id').textContent = data.trip_id;
    document.getElementById('trip-state').textContent = data.state;
    document.getElementById('trip-speed').textContent = data.current_speed;
    document.getElementById('trip-distance').textContent = data.distance_remaining.toFixed(1);
    
    const faultDisplay = document.getElementById('fault-display');
    if (data.state === 'fault_stop') {
        faultDisplay.style.display = 'block';
        faultDisplay.textContent = `Fault: ${data.fault_reason}`;
    } else {
        faultDisplay.style.display = 'none';
    }
};

ws.onclose = function() {
    console.error("Telemetry connection lost. Supervisor unreachable.");
    document.getElementById('trip-state').textContent = "DISCONNECTED";
};

