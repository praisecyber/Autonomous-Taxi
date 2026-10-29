import cv2
import time
import torch
import requests
from yolox.exp import get_exp
from yolox.utils import postprocess
from yolox.data.data_augment import preproc

print("Loading YOLOX Tiny AI Brain...")
exp = get_exp(None, "yolox-tiny")
model = exp.get_model()
model.eval()

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

ckpt = torch.load("taxi/perception/yolox_tiny.pth", map_location="cpu")
model.load_state_dict(ckpt["model"])
print(f"Model successfully loaded on {device}.")

# --- ALL 80 COCO CLASSES (Everything is an obstacle) ---
COCO_CLASSES = [
    "Person", "Bicycle", "Car", "Motorcycle", "Airplane", "Bus", "Train", "Truck", "Boat",
    "Traffic Light", "Fire Hydrant", "Stop Sign", "Parking Meter", "Bench", "Bird", "Cat",
    "Dog", "Horse", "Sheep", "Cow", "Elephant", "Bear", "Zebra", "Giraffe", "Backpack",
    "Umbrella", "Handbag", "Tie", "Suitcase", "Frisbee", "Skis", "Snowboard", "Sports Ball",
    "Kite", "Baseball Bat", "Baseball Glove", "Skateboard", "Surfboard", "Tennis Racket",
    "Bottle", "Wine Glass", "Cup", "Fork", "Knife", "Spoon", "Bowl", "Banana", "Apple",
    "Sandwich", "Orange", "Broccoli", "Carrot", "Hot Dog", "Pizza", "Donut", "Cake",
    "Chair", "Couch", "Potted Plant", "Bed", "Dining Table", "Toilet", "Tv", "Laptop",
    "Mouse", "Remote", "Keyboard", "Cell Phone", "Microwave", "Oven", "Toaster", "Sink",
    "Refrigerator", "Book", "Clock", "Vase", "Scissors", "Teddy Bear", "Hair Drier", "Toothbrush"
]

# Track the last time we sent an alert to prevent spamming the server
last_alert_time = 0.0
is_path_blocked = False

def process_frame(frame):
    global last_alert_time, is_path_blocked
    
    height, width = frame.shape[:2]
    danger_zone = [int(width*0.25), int(height*0.25), int(width*0.75), int(height*0.95)]
    
    overlay = frame.copy()
    cv2.rectangle(overlay, (danger_zone[0], danger_zone[1]), (danger_zone[2], danger_zone[3]), (0, 255, 0), -1)
    cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
    cv2.putText(frame, "DANGER ZONE", (danger_zone[0] + 10, danger_zone[1] + 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    img, ratio = preproc(frame, exp.test_size)
    img = torch.from_numpy(img).unsqueeze(0).float().to(device)
    
    with torch.no_grad():
        outputs = model(img)
        outputs = postprocess(outputs, exp.num_classes, exp.test_conf, exp.nmsthre)[0]
    
    current_frame_has_hazard = False

    if outputs is not None:
        outputs = outputs.cpu().numpy()
        for out in outputs:
            box = out[:4] / ratio
            score = out[4] * out[5]
            class_id = int(out[6])
            
            if score > 0.50 and class_id < len(COCO_CLASSES):
                object_name = COCO_CLASSES[class_id]
                x0, y0, x1, y1 = map(int, box)
                
                in_danger_zone = not (x1 < danger_zone[0] or x0 > danger_zone[2] or 
                                      y1 < danger_zone[1] or y0 > danger_zone[3])
                
                if in_danger_zone:
                    current_frame_has_hazard = True
                    color = (0, 0, 255) 
                    label = f"HAZARD: {object_name} {score*100:.0f}%"
                    
                    if not is_path_blocked:
                        try:
                            alert_data = {"object_name": object_name, "confidence": float(score)}
                            requests.post("http://127.0.0.1:8000/api/vehicle/obstacle", json=alert_data, timeout=0.1)
                            is_path_blocked = True
                        except requests.exceptions.RequestException:
                            pass
                else:
                    color = (0, 255, 255)
                    label = f"Safe: {object_name} {score*100:.0f}%"

                cv2.rectangle(frame, (x0, y0), (x1, y1), color, 2)
                cv2.putText(frame, label, (x0, y0 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
    # If the path was blocked previously, but no hazards are found in this frame
    if is_path_blocked and not current_frame_has_hazard:
        print("AI Brain: Danger Zone is empty! Sending CLEAR command...")
        try:
            # Increased timeout to 0.5s to prevent network drops
            response = requests.post("http://127.0.0.1:8000/api/vehicle/clear", timeout=0.5)
            
            if response.status_code == 200:
                is_path_blocked = False
                print("AI Brain: Server received clear command. Path is clear.")
            else:
                print(f"AI Brain: Server returned Error {response.status_code}. Retrying next frame...")
                
        except requests.exceptions.RequestException as e:
            print(f"AI Brain: Failed to contact server - {e}")
                
    return frame

def run_perception(source):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not connect to {source}.")
        return

    print(f"Starting live perception on: {source}")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        start_time = time.perf_counter()
        
        # Process the frame
        output_frame = process_frame(frame)
        
        latency = time.perf_counter() - start_time
        fps = 1.0 / latency if latency > 0 else 0
        
        # Display the speed
        cv2.putText(output_frame, f"Latency: {latency*1000:.1f}ms | FPS: {fps:.1f}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        cv2.imshow("Member 2 - Autonomous Brain", output_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Test with your laptop webcam (0)
    run_perception(0)