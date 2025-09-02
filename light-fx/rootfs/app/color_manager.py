#!/usr/bin/env python3
"""Color management system for Light FX addon."""
from typing import List, Dict, Union, Tuple
from dataclasses import dataclass
import colorsys
from colour import Color

@dataclass
class ColorPoint:
    """Represents a color point in a palette."""
    color: Color
    position: float = 0  # 0-100

@dataclass
class Palette:
    """Represents a color palette."""
    name: str
    colors: List[ColorPoint]
    type: str = "static"  # static, gradient, or dynamic
    parameters: Dict = None

class ColorManager:
    """Manages color palettes and color conversions."""
    
    def __init__(self):
        self.palettes = {}
        self._init_default_palettes()

    def _init_default_palettes(self):
        """Initialize default color palettes."""
        # Rainbow palette
        rainbow = Palette(
            name="rainbow",
            type="gradient",
            colors=[
                ColorPoint(Color("red"), 0),
                ColorPoint(Color("orange"), 16.6),
                ColorPoint(Color("yellow"), 33.3),
                ColorPoint(Color("green"), 50),
                ColorPoint(Color("blue"), 66.6),
                ColorPoint(Color("indigo"), 83.3),
                ColorPoint(Color("violet"), 100)
            ]
        )
        
        # Fire palette
        fire = Palette(
            name="fire",
            type="dynamic",
            colors=[
                ColorPoint(Color("#ff0000"), 0),
                ColorPoint(Color("#ff8800"), 50),
                ColorPoint(Color("#ffff00"), 100)
            ],
            parameters={"variation": 20}
        )

        self.palettes.update({
            "rainbow": rainbow,
            "fire": fire
        })

    def rgb_to_rgbw(self, rgb: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
        """Convert RGB to RGBW."""
        r, g, b = rgb
        # Extract the white component using the minimum of RGB
        w = min(r, g, b)
        if w > 0:
            r = r - w
            g = g - w
            b = b - w
        return (r, g, b, w)

    def rgb_to_rgbww(self, rgb: Tuple[int, int, int], 
                     color_temp: int = 6500) -> Tuple[int, int, int, int, int]:
        """Convert RGB to RGBWW (RGB + Cold White + Warm White)."""
        r, g, b = rgb
        # First get the white component
        w = min(r, g, b)
        
        # Calculate the distribution between cold and warm white
        # based on color temperature (simplified)
        total_white = w
        if color_temp >= 6500:  # Cold white
            cw = total_white
            ww = 0
        elif color_temp <= 2700:  # Warm white
            cw = 0
            ww = total_white
        else:
            # Linear interpolation between warm and cold
            ratio = (color_temp - 2700) / (6500 - 2700)
            cw = int(total_white * ratio)
            ww = total_white - cw

        if w > 0:
            r = r - w
            g = g - w
            b = b - w

        return (r, g, b, cw, ww)

    def get_color_at_position(self, palette_name: str, position: float) -> Color:
        """Get color at specific position (0-100) in the palette."""
        palette = self.palettes.get(palette_name)
        if not palette:
            raise ValueError(f"Palette {palette_name} not found")

        if palette.type == "static":
            # For static palettes, just return the nearest color
            return min(palette.colors, 
                      key=lambda x: abs(x.position - position)).color

        elif palette.type == "gradient":
            # Find the two colors to interpolate between
            colors = sorted(palette.colors, key=lambda x: x.position)
            
            # Find the two colors surrounding our position
            for i in range(len(colors) - 1):
                if colors[i].position <= position <= colors[i + 1].position:
                    # Linear interpolation between the two colors
                    c1 = colors[i]
                    c2 = colors[i + 1]
                    range_size = c2.position - c1.position
                    if range_size == 0:
                        return c1.color
                    ratio = (position - c1.position) / range_size
                    return self._interpolate_color(c1.color, c2.color, ratio)

            # If we're outside the range, return the nearest color
            return colors[-1].color if position > colors[-1].position else colors[0].color

    def _interpolate_color(self, color1: Color, color2: Color, ratio: float) -> Color:
        """Interpolate between two colors using HSV color space."""
        # Convert to HSV for better interpolation
        hsv1 = colorsys.rgb_to_hsv(*color1.rgb)
        hsv2 = colorsys.rgb_to_hsv(*color2.rgb)
        
        # Interpolate in HSV space
        h = self._interpolate_hue(hsv1[0], hsv2[0], ratio)
        s = hsv1[1] + (hsv2[1] - hsv1[1]) * ratio
        v = hsv1[2] + (hsv2[2] - hsv1[2]) * ratio
        
        # Convert back to RGB
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return Color(rgb=rgb)

    def _interpolate_hue(self, h1: float, h2: float, ratio: float) -> float:
        """Interpolate hue the short way around the color wheel."""
        diff = h2 - h1
        if diff > 0.5:
            h2 -= 1.0
        elif diff < -0.5:
            h2 += 1.0
        h = h1 + (h2 - h1) * ratio
        if h < 0:
            h += 1.0
        elif h > 1:
            h -= 1.0
        return h
