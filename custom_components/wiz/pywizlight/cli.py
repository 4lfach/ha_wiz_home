"""Command-line interface to interact with wizlight discovered_devices."""
import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import click

from pywizlight import PilotBuilder, discovery, wizlight
from pywizlight.home import wizhome

T = TypeVar("T")


def coro(f: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Allow to use async in click."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        """Async wrapper."""
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@click.group()
@click.version_option()
def main() -> None:
    """Command-line tool to interact with Wizlight discovered_devices."""


@main.command("discover")
@coro
@click.option(
    "--b",
    prompt="Set the broadcast address",
    help="Define the broadcast address like 192.168.1.255.",
)
async def discover(b: str) -> None:
    """Discovery device in the local network."""
    click.echo(f"Search for discovered_devices using {b} ... ")

    homes = []
    wiz_office = wizhome(None, None, "Enterprise_HomeStructure.json")
    await wiz_office.fetchJSONContent(asyncio.get_event_loop())
    wiz_office.parseJSON()
    homes.append(wiz_office)

    wiz_lab = wizhome(None, None, "LabConnectivityTest_HomeStructure.json")
    await wiz_lab.fetchJSONContent(asyncio.get_event_loop())
    wiz_lab.parseJSON()
    homes.append(wiz_lab)

    located_devices = {}

    discovered_devices = await discovery.find_wizlights(broadcast_address=b)

    for wh in homes:
        if wh.jsonHome:
            click.echo(f"Devices belonging to the current Home: {wh.homeID} / {wh.name}")
        else:
            click.echo("Devices found (no Home structure information provided )")

        for device in discovered_devices[:128]:
            try:
                details = wh.get_device_details(device.mac_address)
                if details:
                    located_devices.update({device.ip_address: device})
                    room_id = details.get('room_id')
                    room = wh.rooms.get(room_id)

                    group_id = details.get('group_id')
                    group = wh.groups.get(group_id)
                    if group:
                        home_path = f'{wh.name}/{room.get('name'):<24}/{group.get('name')}'
                    else:
                        home_path = f'{wh.name}/{room.get('name'):<24}/{group_id}'

                    click.echo(f"{device.ip_address}\t {device.mac_address} \t{home_path:<42} {details.get('name'):42} {details.get('traits')}")
            except AttributeError as ex:
                click.echo(f"{device.ip_address}\t {device.mac_address} ERRROR--> {ex}")
    
    if len(located_devices) < len(discovered_devices):
        if len(homes) > 0:
            click.echo("Unknown Devices")
        for device in discovered_devices[:128]:
            if device.ip_address not in located_devices:
                click.echo(f"{device.ip_address}\t {device.mac_address} ")



@main.command("on")
@coro
@click.option("--ip", prompt="IP address of the device", help="IP address of the device.")
@click.option(
    "--k",
    prompt="Kelvin for temperature.",
    help="Kelvin value (1000-8000) for turn on. Default 3000",
    default=3000,
    type=int,
)
@click.option(
    "--brightness",
    prompt="Set the brightness value 0-255",
    help="Brightness for turn on. Default 128",
    default=128,
    type=int,
)
async def turn_on(ip: str, k: int, brightness: int) -> None:
    """Turn a given device on."""
    click.echo(f"Turning on {ip}")
    device = wizlight(ip)
    if device and 1000 <= k <= 6800 and 0 <= brightness <= 255:
        await device.turn_on(PilotBuilder(colortemp=k, brightness=brightness))
    else:
        click.echo("Error - values are not correct. Type --help for help.")
    await device.async_close()


@main.command("set-state")
@coro
@click.option("--ip", prompt="IP address of the device", help="IP address of the device.")
@click.option(
    "--k",
    prompt="Kelvin for temperature.",
    help="Kelvin value (1000-8000) for turn on. Default 3000",
    default=3000,
)
@click.option(
    "--brightness",
    prompt="Set the brightness value 0-255",
    help="Brightness for turn on. Default 128",
    default=128,
)
async def set_state(ip: str, k: int, brightness: int) -> None:
    """Set the current state of a given device."""
    click.echo(f"Turning on {ip}")
    device = wizlight(ip)
    if device and 1000 <= k <= 6800 and 0 <= brightness <= 255:
        await device.set_state(PilotBuilder(colortemp=k, brightness=brightness))
    else:
        click.echo("Error - values are not correct. Type --help for help.")
    await device.async_close()


@main.command("off")
@coro
@click.option("--ip", prompt="IP address of the device", help="IP address of the device.")
async def turn_off(ip: str) -> None:
    """Turn a given device off."""
    click.echo(f"Turning off {ip}")
    device = wizlight(ip)
    await device.turn_off()
    await device.async_close()


@main.command("state")
@coro
@click.option("--ip", prompt="IP address of the device", help="IP address of the device.")
async def state(ip: str) -> None:
    """Get the current state of a given device."""
    click.echo(f"Get the state from {ip}")
    device = wizlight(ip)
    device_state = await device.updateState()
    if device_state:
        click.echo(device_state.pilotResult)
    else:
        click.echo("Did not get state from device")
    await device.async_close()


if __name__ == "__main__":
    main()
