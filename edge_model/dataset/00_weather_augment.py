"""
Northern Blades — Step 0: Weather Augmentation with Albumentations
Applies fog, rain, sun glare, and smog effects to training images.
Run this BEFORE step 04 to create augmented copies.

Usage:
  pip install albumentations opencv-python
  python 00_weather_augment.py
"""

import os
import cv2
import random
import numpy as np

try:
    import albumentations as A
except ImportError:
    print("Install albumentations: pip install albumentations")
    exit(1)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
INPUT_DIR = "dataset/images/all_raw"
LABEL_DIR = "dataset/labels/all_raw"  # Copy labels for augmented images
AUGMENT_RATIO = 0.30  # Augment 30% of images
SEED = 42
# ─────────────────────────────────────────────────────────────────────────────

# Delhi-specific weather conditions
WEATHER_TRANSFORMS = {
    "dense_fog": A.Compose([
        A.RandomFog(
            fog_coef_lower=0.5,
            fog_coef_upper=0.8,
            alpha_coef=0.3,
            p=1.0
        ),
        A.ColorJitter(
            brightness=(-0.1, 0.1),
            contrast=(-0.2, 0.0),
            saturation=(-0.3, 0.0),
            p=0.8
        ),
    ]),

    "light_smog": A.Compose([
        A.RandomFog(
            fog_coef_lower=0.2,
            fog_coef_upper=0.4,
            alpha_coef=0.5,
            p=1.0
        ),
        A.ColorJitter(
            brightness=(-0.05, 0.05),
            contrast=(-0.1, 0.0),
            hue=(-0.02, 0.02),
            p=0.8
        ),
    ]),

    "sun_glare": A.Compose([
        A.RandomSunFlare(
            flare_roi=(0, 0, 1, 0.5),
            angle_lower=0,
            angle_upper=1,
            num_flare_circles_lower=3,
            num_flare_circles_upper=6,
            src_radius=200,
            p=1.0
        ),
    ]),

    "rain": A.Compose([
        A.RandomRain(
            slant_lower=-10,
            slant_upper=10,
            drop_length=20,
            drop_width=1,
            drop_color=(200, 200, 200),
            blur_value=3,
            brightness_coefficient=0.8,
            rain_type="heavy",
            p=1.0
        ),
    ]),

    "night_low_light": A.Compose([
        A.RandomBrightnessContrast(
            brightness_limit=(-0.4, -0.2),
            contrast_limit=(-0.2, 0.0),
            p=1.0
        ),
        A.GaussNoise(
            var_limit=(20, 50),
            p=0.8
        ),
    ]),

    "motion_blur": A.Compose([
        A.MotionBlur(
            blur_limit=(7, 15),
            p=1.0
        ),
    ]),
}


def main():
    print("=" * 50)
    print("Northern Blades — Weather Augmentation")
    print("=" * 50)

    if not os.path.exists(INPUT_DIR):
        print(f"ERROR: {INPUT_DIR} not found. Run step 01 first!")
        return

    image_exts = {'.jpg', '.jpeg', '.png'}
    all_images = [f for f in os.listdir(INPUT_DIR)
                  if os.path.splitext(f)[1].lower() in image_exts]

    random.seed(SEED)
    num_to_augment = int(len(all_images) * AUGMENT_RATIO)
    selected = random.sample(all_images, min(num_to_augment, len(all_images)))

    print(f"  Total images: {len(all_images)}")
    print(f"  Augmenting:   {len(selected)} ({AUGMENT_RATIO*100:.0f}%)")

    weather_names = list(WEATHER_TRANSFORMS.keys())
    stats = {name: 0 for name in weather_names}
    total_created = 0

    for img_name in selected:
        img_path = os.path.join(INPUT_DIR, img_name)
        image = cv2.imread(img_path)
        if image is None:
            continue

        # Pick a random weather effect
        weather = random.choice(weather_names)
        transform = WEATHER_TRANSFORMS[weather]

        try:
            augmented = transform(image=image)
            aug_image = augmented["image"]

            # Save augmented image
            stem = os.path.splitext(img_name)[0]
            ext = os.path.splitext(img_name)[1]
            aug_name = f"{stem}_aug_{weather}{ext}"
            aug_path = os.path.join(INPUT_DIR, aug_name)
            cv2.imwrite(aug_path, aug_image, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Copy corresponding label file (same bboxes, different weather)
            label_name = f"{stem}.txt"
            label_path = os.path.join(LABEL_DIR, label_name)
            if os.path.exists(label_path):
                aug_label_name = f"{stem}_aug_{weather}.txt"
                aug_label_path = os.path.join(LABEL_DIR, aug_label_name)
                with open(label_path, 'r') as f:
                    content = f.read()
                with open(aug_label_path, 'w') as f:
                    f.write(content)

            stats[weather] += 1
            total_created += 1

        except Exception as e:
            # Some Albumentations transforms can fail on edge cases
            continue

    print(f"\n  Weather distribution:")
    for weather, count in stats.items():
        print(f"    {weather:<20} {count} images")

    print(f"\n  Total augmented images created: {total_created}")
    print(f"  New total: {len(all_images) + total_created} images")
    print(f"\n  Next: Run 04_finalize_dataset.py to split train/val")


if __name__ == "__main__":
    main()
