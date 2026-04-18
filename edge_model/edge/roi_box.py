import cv2
import json
import os
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "roi_config.json")
BOX_IMG = os.path.join(os.path.dirname(SCRIPT_DIR), "testimages", "empty_intersection.jpg")

class BoxROIConfigurator:
    def __init__(self):
        self.points = []
        self.img = cv2.imread(BOX_IMG)
        if self.img is None:
            print(f"[ERROR] Cannot load {BOX_IMG}")
            exit(1)
        self.clone = self.img.copy()

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))

    def run(self):
        cv2.namedWindow("Draw Intersection Box ROI")
        cv2.setMouseCallback("Draw Intersection Box ROI", self._mouse_callback)

        print("\n" + "="*50)
        print("  DRAW 5TH CAMERA INTERSECTION BOX ROI")
        print("  Click to add points. Press 'S' to save and exit.")
        print("  Press 'C' to clear points.")
        print("="*50 + "\n")

        while True:
            temp_img = self.clone.copy()
            if len(self.points) > 0:
                cv2.polylines(temp_img, [np.array(self.points, dtype=np.int32)], True, (0, 0, 255), 2)
                for pt in self.points:
                    cv2.circle(temp_img, pt, 4, (0, 255, 255), -1)

            cv2.imshow("Draw Intersection Box ROI", temp_img)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                self.save()
                break
            elif key == ord('c'):
                self.points = []

        cv2.destroyAllWindows()

    def save(self):
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)

        if "Box" not in config:
            config["Box"] = {}
        config["Box"]["zones"] = {"box": self.points}

        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        print(f"[SAVED] Intersection Box ROI saved to {CONFIG_PATH} with {len(self.points)} points!")

if __name__ == "__main__":
    BoxROIConfigurator().run()
