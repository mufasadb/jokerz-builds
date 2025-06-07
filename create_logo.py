#!/usr/bin/env python3
"""
Logo creation script for Joker Builds
Creates a professional logo combining playing card and building themes
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_logo():
    # Logo dimensions
    width, height = 400, 400
    
    # Create image with transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Color scheme - dark theme with accent colors
    bg_color = (26, 26, 46)  # Dark navy
    primary_color = (220, 53, 69)  # Red for "Joker"
    secondary_color = (255, 193, 7)  # Gold accent
    text_color = (248, 249, 250)  # Light text
    
    # Draw background circle
    margin = 20
    circle_bbox = [margin, margin, width-margin, height-margin]
    draw.ellipse(circle_bbox, fill=bg_color, outline=secondary_color, width=4)
    
    # Draw playing card suit symbols (simplified)
    # Spade symbol at top
    spade_points = [
        (width//2, 80),  # top point
        (width//2 - 25, 120),  # left curve
        (width//2 - 15, 135),  # left bottom
        (width//2 - 5, 140),   # stem left
        (width//2 + 5, 140),   # stem right
        (width//2 + 15, 135),  # right bottom
        (width//2 + 25, 120),  # right curve
    ]
    draw.polygon(spade_points, fill=primary_color)
    
    # Draw building/bar chart elements in center
    bar_width = 20
    bar_spacing = 8
    bars_y_base = 280
    bar_heights = [60, 90, 75, 105, 80]  # Different heights for variety
    
    start_x = width//2 - (len(bar_heights) * (bar_width + bar_spacing) - bar_spacing) // 2
    
    for i, bar_height in enumerate(bar_heights):
        x = start_x + i * (bar_width + bar_spacing)
        y = bars_y_base - bar_height
        
        # Gradient effect - lighter at top
        for j in range(bar_height):
            alpha = int(255 * (0.6 + 0.4 * (bar_height - j) / bar_height))
            color = secondary_color + (alpha,)
            draw.rectangle([x, y + j, x + bar_width, y + j + 1], fill=color)
    
    # Add text
    try:
        # Try to use a nice font, fall back to default
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # "JOKER" text
    joker_text = "JOKER"
    joker_bbox = draw.textbbox((0, 0), joker_text, font=font_large)
    joker_width = joker_bbox[2] - joker_bbox[0]
    joker_x = (width - joker_width) // 2
    draw.text((joker_x, 160), joker_text, fill=primary_color, font=font_large)
    
    # "BUILDS" text
    builds_text = "BUILDS"
    builds_bbox = draw.textbbox((0, 0), builds_text, font=font_small)
    builds_width = builds_bbox[2] - builds_bbox[0]
    builds_x = (width - builds_width) // 2
    draw.text((builds_x, 210), builds_text, fill=text_color, font=font_small)
    
    # Add small decorative elements
    # Small diamonds around the logo
    diamond_size = 6
    positions = [(100, 100), (300, 100), (100, 300), (300, 300)]
    for x, y in positions:
        diamond_points = [
            (x, y - diamond_size),  # top
            (x + diamond_size, y),  # right
            (x, y + diamond_size),  # bottom
            (x - diamond_size, y)   # left
        ]
        draw.polygon(diamond_points, fill=secondary_color)
    
    return img

def main():
    """Create and save the logo"""
    print("Creating Joker Builds logo...")
    
    # Create logo
    logo = create_logo()
    
    # Save in multiple formats
    logo_dir = "assets"
    if not os.path.exists(logo_dir):
        os.makedirs(logo_dir)
    
    # Save as PNG (with transparency)
    png_path = os.path.join(logo_dir, "joker_builds_logo.png")
    logo.save(png_path, "PNG")
    print(f"Logo saved as: {png_path}")
    
    # Save as JPG (with white background for compatibility)
    jpg_logo = Image.new('RGB', logo.size, (255, 255, 255))
    jpg_logo.paste(logo, mask=logo.split()[3] if len(logo.split()) == 4 else None)
    jpg_path = os.path.join(logo_dir, "joker_builds_logo.jpg")
    jpg_logo.save(jpg_path, "JPEG", quality=95)
    print(f"Logo saved as: {jpg_path}")
    
    # Create a smaller version for favicon/icon use
    icon_size = (64, 64)
    icon = logo.resize(icon_size, Image.Resampling.LANCZOS)
    icon_path = os.path.join(logo_dir, "joker_builds_icon.png")
    icon.save(icon_path, "PNG")
    print(f"Icon saved as: {icon_path}")
    
    print("Logo creation complete!")
    return png_path

if __name__ == "__main__":
    main()