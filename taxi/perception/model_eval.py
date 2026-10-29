import cv2
import time
import torch
import argparse
from yolox.exp import get_exp
from yolox.utils import postprocess
from yolox.data.data_augment import preproc

def benchmark_model(model_name, weight_file, num_frames=100):
    print(f"\n--- Starting Benchmark for {model_name.upper()} ---")
    
    # 1. Load Model
    exp = get_exp(None, model_name)
    model = exp.get_model()
    model.eval()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    
    try:
        ckpt = torch.load(weight_file, map_location="cpu")
        model.load_state_dict(ckpt["model"])
        print(f"[{model_name}] Weights loaded successfully on {device}.")
    except FileNotFoundError:
        print(f"Error: {weight_file} not found. Please download it to this folder.")
        return

    # 2. Warm up the camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not connect to webcam.")
        return
        
    print(f"[{model_name}] Warming up camera...")
    for _ in range(10):
        cap.read()
        
    print(f"[{model_name}] Running test for {num_frames} frames...")
    
    total_time = 0.0
    frames_processed = 0
    detections_found = 0

    # 3. Run Benchmark
    while frames_processed < num_frames:
        ret, frame = cap.read()
        if not ret:
            break

        # Start timer for this frame
        start_time = time.perf_counter()
        
        img, ratio = preproc(frame, exp.test_size)
        img = torch.from_numpy(img).unsqueeze(0).float().to(device)
        
        with torch.no_grad():
            outputs = model(img)
            outputs = postprocess(outputs, exp.num_classes, exp.test_conf, exp.nmsthre)[0]
            
        # Stop timer
        latency = time.perf_counter() - start_time
        total_time += latency
        
        if outputs is not None:
            detections_found += len(outputs)
            
        frames_processed += 1
        
        # Display progress
        cv2.putText(frame, f"Benchmarking: {model_name} | Frame {frames_processed}/{num_frames}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Benchmarking", frame)
        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()

    # 4. Calculate Metrics
    if frames_processed == 0:
        print(f"\n[{model_name}] ERROR: Camera failed. 0 frames processed. Is another script using the webcam?")
        return

    avg_latency_ms = (total_time / frames_processed) * 1000
    avg_fps = frames_processed / total_time
    
    print("\n==========================================")
    print(f" RESULTS: {model_name.upper()}")
    print("==========================================")
    print(f" Hardware:      {device.upper()}")
    print(f" Avg Latency:   {avg_latency_ms:.2f} ms per frame")
    print(f" Average FPS:   {avg_fps:.2f} FPS")
    print(f" Total Objects: {detections_found} detected in {num_frames} frames")
    print("==========================================\n")

if __name__ == "__main__":
    # Standardize test lengths
    FRAMES = 150
    
    # Test 1: Nano (Smallest, Fastest, Lowest Accuracy)
    benchmark_model("yolox-nano", "taxi/perception/yolox_nano.pth", FRAMES)
    
    # Test 2: Tiny (Balanced)
    benchmark_model("yolox-tiny", "taxi/perception/yolox_tiny.pth", FRAMES)
    
    # Test 3: S (Standard - Heaviest, Slowest, Highest Accuracy)
    benchmark_model("yolox-s", "taxi/perception/yolox_s.pth", FRAMES)