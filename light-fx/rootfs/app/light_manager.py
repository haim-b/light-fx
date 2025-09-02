"""Light management system for Light FX addon."""
from typing import List, Dict, Any, Optional
import logging
import asyncio
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

@dataclass
class LightCapabilities:
    """Represents the capabilities of a light entity."""
    supports_rgb: bool = False
    supports_rgbw: bool = False
    supports_rgbww: bool = False
    supports_color_temp: bool = False
    min_mireds: Optional[int] = None
    max_mireds: Optional[int] = None
    supports_transition: bool = False
    supports_brightness: bool = False

@dataclass
class LightState:
    """Represents the current state of a light."""
    entity_id: str
    state: str  # on/off
    brightness: Optional[int] = None
    rgb_color: Optional[tuple] = None
    rgbw_color: Optional[tuple] = None
    rgbww_color: Optional[tuple] = None
    color_temp: Optional[int] = None

class LightSequence:
    """Represents an ordered sequence of lights."""
    def __init__(self, name: str, lights: List[str]):
        self.name = name
        self.light_ids = lights
        self.states: Dict[str, LightState] = {}
        self.capabilities: Dict[str, LightCapabilities] = {}

class LightManager:
    """Manages light entities and their states."""
    
    def __init__(self, ha_api):
        self.ha_api = ha_api
        self.sequences: Dict[str, LightSequence] = {}
        self.light_states: Dict[str, LightState] = {}
        self._update_lock = asyncio.Lock()

    async def create_sequence(self, name: str, light_ids: List[str]) -> LightSequence:
        """Create a new light sequence."""
        sequence = LightSequence(name, light_ids)
        # Fetch initial states and capabilities
        for entity_id in light_ids:
            await self._fetch_capabilities(entity_id, sequence)
            await self._fetch_state(entity_id, sequence)
        self.sequences[name] = sequence
        return sequence

    async def _fetch_capabilities(self, entity_id: str, sequence: LightSequence):
        """Fetch capabilities of a light entity."""
        try:
            state = await self.ha_api.get_state(entity_id)
            attributes = state.get('attributes', {})
            
            caps = LightCapabilities(
                supports_rgb='rgb_color' in attributes.get('supported_color_modes', []),
                supports_rgbw='rgbw' in attributes.get('supported_color_modes', []),
                supports_rgbww='rgbww' in attributes.get('supported_color_modes', []),
                supports_color_temp='color_temp' in attributes.get('supported_color_modes', []),
                min_mireds=attributes.get('min_mireds'),
                max_mireds=attributes.get('max_mireds'),
                supports_transition='transition' in attributes,
                supports_brightness='brightness' in attributes
            )
            
            sequence.capabilities[entity_id] = caps
            
        except Exception as e:
            _LOGGER.error(f"Error fetching capabilities for {entity_id}: {e}")
            raise

    async def _fetch_state(self, entity_id: str, sequence: LightSequence):
        """Fetch current state of a light entity."""
        try:
            state = await self.ha_api.get_state(entity_id)
            attributes = state.get('attributes', {})
            
            light_state = LightState(
                entity_id=entity_id,
                state=state.get('state'),
                brightness=attributes.get('brightness'),
                rgb_color=tuple(attributes['rgb_color']) if 'rgb_color' in attributes else None,
                rgbw_color=tuple(attributes['rgbw_color']) if 'rgbw_color' in attributes else None,
                rgbww_color=tuple(attributes['rgbww_color']) if 'rgbww_color' in attributes else None,
                color_temp=attributes.get('color_temp')
            )
            
            sequence.states[entity_id] = light_state
            self.light_states[entity_id] = light_state
            
        except Exception as e:
            _LOGGER.error(f"Error fetching state for {entity_id}: {e}")
            raise

    async def update_light(self, entity_id: str, **kwargs):
        """Update a light entity's state."""
        async with self._update_lock:
            try:
                await self.ha_api.call_service(
                    'light', 'turn_on',
                    {'entity_id': entity_id, **kwargs}
                )
                # Wait a bit for the state to update
                await asyncio.sleep(0.1)
                # Update our stored state
                for sequence in self.sequences.values():
                    if entity_id in sequence.light_ids:
                        await self._fetch_state(entity_id, sequence)
                        
            except Exception as e:
                _LOGGER.error(f"Error updating light {entity_id}: {e}")
                raise

    async def turn_off_sequence(self, sequence_name: str):
        """Turn off all lights in a sequence."""
        sequence = self.sequences.get(sequence_name)
        if not sequence:
            raise ValueError(f"Sequence {sequence_name} not found")
            
        for entity_id in sequence.light_ids:
            try:
                await self.ha_api.call_service(
                    'light', 'turn_off',
                    {'entity_id': entity_id}
                )
            except Exception as e:
                _LOGGER.error(f"Error turning off light {entity_id}: {e}")

    def get_sequence(self, name: str) -> Optional[LightSequence]:
        """Get a sequence by name."""
        return self.sequences.get(name)
