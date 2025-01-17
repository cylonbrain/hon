import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntityDescription, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from pyhon import Hon
from pyhon.appliance import HonAppliance
from pyhon.parameter.range import HonParameterRange

from .const import DOMAIN
from .hon import HonCoordinator, HonEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class HonSwitchEntityDescriptionMixin:
    turn_on_key: str = ""
    turn_off_key: str = ""


@dataclass
class HonSwitchEntityDescription(
    HonSwitchEntityDescriptionMixin, SwitchEntityDescription
):
    pass


SWITCHES: dict[str, tuple[HonSwitchEntityDescription, ...]] = {
    "WM": (
        HonSwitchEntityDescription(
            key="active",
            name="Washing Machine",
            icon="mdi:washing-machine",
            turn_on_key="startProgram",
            turn_off_key="stopProgram",
        ),
        HonSwitchEntityDescription(
            key="pause",
            name="Pause Washing Machine",
            icon="mdi:pause",
            turn_on_key="pauseProgram",
            turn_off_key="resumeProgram",
        ),
        HonSwitchEntityDescription(
            key="startProgram.delayStatus",
            name="Delay Status",
            icon="mdi:timer-check",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.haier_SoakPrewashSelection",
            name="Soak Prewash Selection",
            icon="mdi:tshirt-crew",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    "TD": (
        HonSwitchEntityDescription(
            key="active",
            name="Tumble Dryer",
            icon="mdi:tumble-dryer",
            turn_on_key="startProgram",
            turn_off_key="stopProgram",
        ),
        HonSwitchEntityDescription(
            key="pause",
            name="Pause Tumble Dryer",
            icon="mdi:pause",
            turn_on_key="pauseProgram",
            turn_off_key="resumeProgram",
        ),
    ),
    "WD": (
        HonSwitchEntityDescription(
            key="active",
            name="Washing Machine",
            icon="mdi:washing-machine",
            turn_on_key="startProgram",
            turn_off_key="stopProgram",
        ),
        HonSwitchEntityDescription(
            key="pause",
            name="Pause Washing Machine",
            icon="mdi:pause",
            turn_on_key="pauseProgram",
            turn_off_key="resumeProgram",
        ),
    ),
    "DW": (
        HonSwitchEntityDescription(
            key="active",
            name="Dish Washer",
            icon="mdi:dishwasher",
            turn_on_key="startProgram",
            turn_off_key="stopProgram",
        ),
        HonSwitchEntityDescription(
            key="startProgram.extraDry",
            name="Extra Dry",
            icon="mdi:hair-dryer",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.halfLoad",
            name="Half Load",
            icon="mdi:fraction-one-half",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.openDoor",
            name="Open Door",
            icon="mdi:door-open",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.threeInOne",
            name="Three in One",
            icon="mdi:numeric-3-box-outline",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.ecoExpress",
            name="Eco Express",
            icon="mdi:sprout",
            entity_category=EntityCategory.CONFIG,
        ),
        HonSwitchEntityDescription(
            key="startProgram.addDish",
            name="Add Dish",
            icon="mdi:silverware-fork-knife",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
}


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    hon: Hon = hass.data[DOMAIN][entry.unique_id]
    coordinators = hass.data[DOMAIN]["coordinators"]
    appliances = []
    for device in hon.appliances:
        if device.unique_id in coordinators:
            coordinator = hass.data[DOMAIN]["coordinators"][device.unique_id]
        else:
            coordinator = HonCoordinator(hass, device)
            hass.data[DOMAIN]["coordinators"][device.unique_id] = coordinator
        await coordinator.async_config_entry_first_refresh()

        if descriptions := SWITCHES.get(device.appliance_type):
            for description in descriptions:
                if (
                    device.get(description.key) is not None
                    or device.commands.get(description.key) is not None
                ):
                    appliances.extend(
                        [HonSwitchEntity(hass, coordinator, entry, device, description)]
                    )
                else:
                    _LOGGER.warning(
                        "[%s] Can't setup %s", device.appliance_type, description.key
                    )

    async_add_entities(appliances)


class HonSwitchEntity(HonEntity, SwitchEntity):
    entity_description: HonSwitchEntityDescription

    def __init__(
        self,
        hass,
        coordinator,
        entry,
        device: HonAppliance,
        description: HonSwitchEntityDescription,
    ) -> None:
        super().__init__(hass, entry, coordinator, device)
        self._coordinator = coordinator
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if self.entity_category == EntityCategory.CONFIG:
            setting = self._device.settings[self.entity_description.key]
            return (
                setting.value == "1"
                or hasattr(setting, "min")
                and setting.value != setting.min
            )
        return self._device.get(self.entity_description.key, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.entity_category == EntityCategory.CONFIG:
            setting = self._device.settings[self.entity_description.key]
            setting.value = (
                setting.max if isinstance(setting, HonParameterRange) else "1"
            )
            self.async_write_ha_state()
        else:
            await self._device.commands[self.entity_description.turn_on_key].send()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.entity_category == EntityCategory.CONFIG:
            setting = self._device.settings[self.entity_description.key]
            setting.value = (
                setting.min if isinstance(setting, HonParameterRange) else "0"
            )
            self.async_write_ha_state()
        else:
            await self._device.commands[self.entity_description.turn_off_key].send()
