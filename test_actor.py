import pytest
import importlib
from unittest.mock import patch, call, MagicMock, Mock, AsyncMock
from cbpi.api import *
import logging
import sys
from configparser import ConfigParser
import asyncio
import os

config = ConfigParser()

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
    # Fake GPIO mock
    fake_gpio = MagicMock()
    fake_gpio.OUT = "OUT"
    fake_gpio.LOW = "LOW"
    fake_gpio.HIGH = "HIGH"

    sys.modules["RPi.GPIO"] = fake_gpio

    # Ensure the SUT is reloaded fresh each time
    if "cbpi4-TimedCycleActor.timed_cycle_actor" in sys.modules:
        del sys.modules["cbpi4-TimedCycleActor.timed_cycle_actor"]

    TimedCycleActor = importlib.import_module("cbpi4-TimedCycleActor.timed_cycle_actor")

    mock_cbpi= Mock()
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
async def test_run_iteration_gpio_cycle(timed_cycle, mock_sleep):
    """Test that one iteration of the run loop cycles GPIO correctly."""
    # Arrange
    actor, fake_gpio = timed_cycle
    await actor.on_start()
    await actor.on()

    ######  Act  ######
    await actor.run_iteration()
    await mock_sleep.original_sleep(0)

    ##### Assert  #####
    logger.debug("Test: GPIO output calls: %s", fake_gpio.output.call_args_list)
    fake_gpio.output.assert_has_calls([call(25, 'LOW'), call(25, 'HIGH'), call(25, 'LOW')])