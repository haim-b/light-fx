"""Main application for Light FX addon."""
import asyncio
import logging
import json
import os
from typing import Dict, Any

from .ha_api import HomeAssistantAPI
from .light_manager import LightManager
from .color_manager import ColorManager
from .effect_engine import EffectEngine, EffectConfig

_LOGGER = logging.getLogger(__name__)

class LightFX:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        # Load config
        with open('/data/options.json') as f:
            self.config = json.load(f)
            
        # Setup Home Assistant API
        self.ha_api = HomeAssistantAPI(
            host = os.environ.get('SUPERVISOR_HOST', 'supervisor'),
            token = os.environ.get('SUPERVISOR_TOKEN'),
            port = 8123
        )
        
        # Initialize managers
        self.color_manager = ColorManager()
        self.light_manager = LightManager(self.ha_api)
        self.effect_engine = EffectEngine(self.light_manager, self.color_manager)
        
    async def setup(self):
        """Set up the application."""
        # Create sequences from config
        for seq_config in self.config.get('sequences', []):
            try:
                await self.light_manager.create_sequence(
                    seq_config['name'],
                    seq_config['lights']
                )
                _LOGGER.info(f"Created sequence: {seq_config['name']}")
                
                # Start default effect if configured
                if seq_config.get('default_effect'):
                    config = EffectConfig(
                        speed=seq_config.get('default_speed', 50),
                        palette_name=seq_config.get('default_palette', 'rainbow')
                    )
                    await self.effect_engine.start_effect(
                        seq_config['name'],
                        seq_config['default_effect'],
                        config
                    )
                    
            except Exception as e:
                _LOGGER.error(f"Error setting up sequence {seq_config['name']}: {e}")
                
    async def handle_service_call(self, call):
        """Handle service calls from Home Assistant."""
        try:
            if call['service'] == 'start_effect':
                await self.effect_engine.start_effect(
                    call['data']['sequence'],
                    call['data']['effect'],
                    EffectConfig(**call['data'].get('config', {}))
                )
                
            elif call['service'] == 'stop_effect':
                await self.effect_engine.stop_effect(
                    call['data']['sequence']
                )
                
        except Exception as e:
            _LOGGER.error(f"Error handling service call: {e}")
            
    async def run(self):
        """Run the application."""
        try:
            await self.setup()
            
            # Register services
            services = {
                'start_effect': {
                    'schema': {
                        'sequence': str,
                        'effect': str,
                        'config': {
                            'speed': int,
                            'intensity': int,
                            'palette_name': str,
                            'reverse': bool,
                            'mirror': bool
                        }
                    }
                },
                'stop_effect': {
                    'schema': {
                        'sequence': str
                    }
                }
            }
            
            # Start event subscription
            await self.ha_api.subscribe_to_events(
                'light_fx_service_call',
                self.handle_service_call
            )
            
            # Keep the application running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            _LOGGER.error(f"Application error: {e}")
            raise
            
        finally:
            # Cleanup
            for sequence_name in list(self.effect_engine._running_effects.keys()):
                await self.effect_engine.stop_effect(sequence_name)
            await self.ha_api.close()

def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO)
    
    app = LightFX()
    asyncio.run(app.run())

if __name__ == "__main__":
    main()
