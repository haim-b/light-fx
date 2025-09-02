"""Effect engine for Light FX addon."""
from typing import List, Dict, Any, Optional, Callable
import asyncio
import time
import math
import random
from dataclasses import dataclass
from colour import Color

from .color_manager import ColorManager, Palette
from .light_manager import LightManager, LightSequence

@dataclass
class EffectConfig:
    """Configuration for an effect."""
    speed: int = 50  # 1-100
    intensity: int = 100  # 1-100
    palette_name: str = "rainbow"
    reverse: bool = False
    mirror: bool = False

class Effect:
    """Base class for all effects."""
    
    def __init__(self, color_manager: ColorManager):
        self.color_manager = color_manager
        self._frame = 0
        self._start_time = time.time()

    async def generate_frame(self, sequence: LightSequence, config: EffectConfig) -> Dict[str, Dict]:
        """Generate the next frame of the effect."""
        raise NotImplementedError()

class RainbowEffect(Effect):
    """Rainbow wave effect."""
    
    async def generate_frame(self, sequence: LightSequence, config: EffectConfig) -> Dict[str, Dict]:
        num_lights = len(sequence.light_ids)
        speed_factor = config.speed / 50  # normalize to 1 at speed 50
        
        # Calculate base offset based on time
        time_offset = (time.time() - self._start_time) * speed_factor
        
        updates = {}
        for i, light_id in enumerate(sequence.light_ids):
            # Calculate position in rainbow (0-100)
            pos = ((i / num_lights) * 100 + time_offset * 20) % 100
            if config.reverse:
                pos = 100 - pos
                
            color = self.color_manager.get_color_at_position("rainbow", pos)
            
            # Apply intensity
            rgb = [int(c * config.intensity / 100) for c in [color.red * 255, color.green * 255, color.blue * 255]]
            
            updates[light_id] = {"rgb_color": rgb}
            
            # Handle mirroring
            if config.mirror and i >= num_lights // 2:
                mirror_i = num_lights - 1 - i
                updates[sequence.light_ids[mirror_i]] = updates[light_id]
        
        return updates

class ColorWipeEffect(Effect):
    """Color wipe effect."""
    
    async def generate_frame(self, sequence: LightSequence, config: EffectConfig) -> Dict[str, Dict]:
        num_lights = len(sequence.light_ids)
        speed_factor = config.speed / 50
        
        # Calculate which lights should be on based on time
        time_offset = (time.time() - self._start_time) * speed_factor
        active_lights = int((time_offset * 2) % (num_lights + 1))
        
        updates = {}
        palette = self.color_manager.palettes[config.palette_name]
        
        for i, light_id in enumerate(sequence.light_ids):
            if config.reverse:
                i = num_lights - 1 - i
                
            if i < active_lights:
                color = self.color_manager.get_color_at_position(
                    config.palette_name,
                    (i / num_lights) * 100
                )
                rgb = [int(c * config.intensity / 100) for c in [color.red * 255, color.green * 255, color.blue * 255]]
                updates[light_id] = {"rgb_color": rgb}
            else:
                updates[light_id] = {"rgb_color": [0, 0, 0]}
        
        return updates

class TwinkleEffect(Effect):
    """Twinkle effect."""
    
    def __init__(self, color_manager: ColorManager):
        super().__init__(color_manager)
        self._twinkle_states = {}
        
    async def generate_frame(self, sequence: LightSequence, config: EffectConfig) -> Dict[str, Dict]:
        updates = {}
        speed_factor = config.speed / 50
        
        # Initialize twinkle states if needed
        for light_id in sequence.light_ids:
            if light_id not in self._twinkle_states:
                self._twinkle_states[light_id] = 0
        
        # Update twinkle states
        for light_id in sequence.light_ids:
            if self._twinkle_states[light_id] == 0:
                # Start new twinkle?
                if random.random() < 0.1 * speed_factor:
                    self._twinkle_states[light_id] = 1
                    color = self.color_manager.get_color_at_position(
                        config.palette_name,
                        random.uniform(0, 100)
                    )
                    rgb = [int(c * config.intensity / 100) for c in [color.red * 255, color.green * 255, color.blue * 255]]
                    updates[light_id] = {"rgb_color": rgb}
                else:
                    updates[light_id] = {"rgb_color": [0, 0, 0]}
            else:
                # Fade existing twinkle
                self._twinkle_states[light_id] -= 0.1 * speed_factor
                if self._twinkle_states[light_id] <= 0:
                    self._twinkle_states[light_id] = 0
                    updates[light_id] = {"rgb_color": [0, 0, 0]}
                else:
                    color = self.color_manager.get_color_at_position(
                        config.palette_name,
                        random.uniform(0, 100)
                    )
                    intensity = self._twinkle_states[light_id] * config.intensity / 100
                    rgb = [int(c * intensity) for c in [color.red * 255, color.green * 255, color.blue * 255]]
                    updates[light_id] = {"rgb_color": rgb}
        
        return updates

class EffectEngine:
    """Manages and runs effects on light sequences."""
    
    def __init__(self, light_manager: LightManager, color_manager: ColorManager):
        self.light_manager = light_manager
        self.color_manager = color_manager
        self.effects = {
            'rainbow': RainbowEffect(color_manager),
            'color_wipe': ColorWipeEffect(color_manager),
            'twinkle': TwinkleEffect(color_manager)
        }
        self._running_effects: Dict[str, tuple] = {}  # sequence_name: (effect, config, task)
        self._frame_delay = 0.05  # 20 FPS default

    async def start_effect(self, sequence_name: str, effect_name: str, config: EffectConfig):
        """Start an effect on a sequence."""
        # Stop any running effect on this sequence
        await self.stop_effect(sequence_name)
        
        sequence = self.light_manager.get_sequence(sequence_name)
        if not sequence:
            raise ValueError(f"Sequence {sequence_name} not found")
            
        effect = self.effects.get(effect_name)
        if not effect:
            raise ValueError(f"Effect {effect_name} not found")
            
        # Create and start the effect task
        task = asyncio.create_task(self._run_effect(sequence, effect, config))
        self._running_effects[sequence_name] = (effect, config, task)

    async def stop_effect(self, sequence_name: str):
        """Stop an effect on a sequence."""
        if sequence_name in self._running_effects:
            effect, config, task = self._running_effects[sequence_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._running_effects[sequence_name]
            # Turn off all lights in the sequence
            await self.light_manager.turn_off_sequence(sequence_name)

    async def _run_effect(self, sequence: LightSequence, effect: Effect, config: EffectConfig):
        """Run an effect continuously."""
        try:
            while True:
                # Generate and apply the next frame
                updates = await effect.generate_frame(sequence, config)
                
                # Apply updates to all lights
                for entity_id, params in updates.items():
                    await self.light_manager.update_light(entity_id, **params)
                
                # Wait for next frame
                await asyncio.sleep(self._frame_delay)
                
        except asyncio.CancelledError:
            # Clean up if needed
            raise
