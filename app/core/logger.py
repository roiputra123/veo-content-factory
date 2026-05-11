import json
import os
from datetime import datetime

class ProductionLogger:
    def __init__(self, registry_dir="storage/registry"):
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)

    def info(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] INFO: {message}")

    def warning(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] WARNING: {message}")

    def error(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ERROR: {message}")

    def log_job(self, job_data):
        job_id = job_data.get("job_id", f"EC-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        file_path = os.path.join(self.registry_dir, f"{job_id}.json")
        
        with open(file_path, "w") as f:
            json.dump(job_data, f, indent=4)
        
        self.info(f"Job {job_id} logged to registry.")
        return job_id
