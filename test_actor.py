import pytest
import importlib
import types
from unittest.mock import patch, call, MagicMock, Mock, AsyncMock
import logging
import sys
import asyncio

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

@pytest.fixture
def mock_sleep(monkeypatch):
    original_sleep = asyncio.sleep
    mock = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", mock)
    mock.original_sleep = original_sleep
    yield mock

@pytest.fixture
def timed_cycle(monkeypatch):
    # Fake GPIO module
    fake_gpio = types.ModuleType("RPi.GPIO")
    fake_gpio.OUT = "OUT"
    fake_gpio.LOW = "LOW"
    fake_gpio.HIGH = "HIGH"
    fake_gpio.BCM = "BCM"
    fake_gpio.getmode = MagicMock(return_value=None)
    fake_gpio.setmode = MagicMock()
    fake_gpio.setup = MagicMock()
    fake_gpio.output = MagicMock()

    rpi_pkg = types.ModuleType("RPi")
    rpi_pkg.__path__ = [""]
    rpi_pkg.GPIO = fake_gpio

    # Mock cbpi modules required by the actor import
    cbpi_mod = types.ModuleType("cbpi")
    cbpi_api_mod = types.ModuleType("cbpi.api")
    cbpi_dataclasses_mod = types.ModuleType("cbpi.api.dataclasses")

    class MockCBPiActorBase:
        def __init__(self, cbpi, id, props):
            self.cbpi = cbpi
            self.id = id
            self.props = props
            self.running = False

    cbpi_api_mod.CBPiActor = MockCBPiActorBase
    cbpi_api_mod.parameters = lambda *args, **kwargs: lambda cls: cls
    cbpi_api_mod.Property = types.SimpleNamespace(Number=lambda *args, **kwargs: None)
    cbpi_dataclasses_mod.NotificationType = types.SimpleNamespace(
        INFO="INFO",
        WARNING="WARNING",
        ERROR="ERROR"
    )

    sys.modules["RPi"] = rpi_pkg
    sys.modules["RPi.GPIO"] = fake_gpio
    sys.modules["cbpi"] = cbpi_mod
    sys.modules["cbpi.api"] = cbpi_api_mod
    sys.modules["cbpi.api.dataclasses"] = cbpi_dataclasses_mod

    # Ensure the SUT is reloaded fresh each time
    if "cbpi4-TimedCycleActor.timed_cycle_actor" in sys.modules:
        del sys.modules["cbpi4-TimedCycleActor.timed_cycle_actor"]

    TimedCycleActor = importlib.import_module("cbpi4-TimedCycleActor.timed_cycle_actor")

    mock_cbpi = Mock()
    mock_cbpi.actor = Mock()
    mock_cbpi.actor.actor_update = AsyncMock(return_value="ok")

    props = {
        "GPIO_Control": 25,
        "on_time": 10,
        "cycle_time": 1
    }

    timed_cycle_actor = TimedCycleActor.TimedCycleActor(mock_cbpi, "ID", props)

    yield timed_cycle_actor, fake_gpio

@pytest.mark.asyncio
async def test_actor_initialization(timed_cycle):
    """Test that the TimedCycleActor initializes correctly."""
    print("Testing TimedCycleActor initialization...")

    ####  Arrange  ####
    actor, fake_gpio = timed_cycle

    ######  Act  ######
    try:
        await actor.on_start()

    ##### Assert  #####
    except Exception as e:
        assert False, f"Initialization raised an exception: {e}"

@pytest.mark.asyncio
async def test_gpio_pin_is_high_10s_then_low_50s(timed_cycle, mock_sleep):
    """Test that the GPIO pin is high for 10 seconds then low for 50 seconds."""
    actor, fake_gpio = timed_cycle
    await actor.on_start()
    await actor.on()

    fake_gpio.output.reset_mock()

    ######  Act  ######
    for i in range(actor.cycle_time * 60*2):
        actor.run_iteration()

    ##### Assert  #####
    logger.debug(f"GPIO output call args: {fake_gpio.output.call_args_list}")
    assert fake_gpio.output.call_args_list == [
        call(25, fake_gpio.HIGH),
        call(25, fake_gpio.LOW),
        call(25, fake_gpio.HIGH),
        call(25, fake_gpio.LOW)
    ]
