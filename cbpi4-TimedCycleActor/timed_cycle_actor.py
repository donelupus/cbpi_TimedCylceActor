# -*- coding: utf-8 -*-
import logging
import asyncio
import importlib
from cbpi.api import *
import RPi.GPIO as GPIO
import os
from cbpi.api.dataclasses import NotificationType


mode = GPIO.getmode()
if mode == None:
    GPIO.setmode(GPIO.BCM)
    
class Logger():
    def __init__(self,cbpi):
        self.cbpi=cbpi
        self.logger = logging.getLogger(__name__)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)
        self.cbpi.notify("StepperMotorActor", message, NotificationType.INFO)

    def warning(self, message):
        self.logger.warning(message)
        self.cbpi.notify("StepperMotorActor", message, NotificationType.WARNING)

    def error(self, message):
        self.logger.error(message)
        self.cbpi.notify("StepperMotorActor", message, NotificationType.ERROR)

@parameters([Property.Number(label="GPIO_Control", description="GPIO [BMC numbering] of upper Level Sensor"), 
            Property.Number(label="on_time",default_value = 90, description="The time in seconds the actor will be switched on every cycle_time min."),
            Property.Number(label="cycle_time",default_value = 12, description="The time in minutes between every on_time period.")])


class TimedCycleActor(CBPiActor):

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self.logger = Logger(cbpi)
        self.logger.debug("Init called")

    
    async def on_start(self):
        '''
        This method defines initial variables for the actor instance.
        '''
        self.logger.debug("TimedCycleActor - On_start method called")

        self.gpio_control = int(self.props.get("GPIO_Control", None))
        self.on_time = int(self.props.get("on_time", 90))
        self.cycle_time = int(self.props.get("cycle_time", 12))

        GPIO.setup(int(self.gpio_control), GPIO.OUT)
        GPIO.output(int(self.gpio_control), GPIO.LOW)

        self.state = False
        self.counter = 0
        self.logger.debug(f"Variable state: {self.state}")
    
        pass

    async def on(self, power=0):
        '''
        This asyncio coroutine defines what needs to be done to switch the actor on.
        :param power: power to be set
        '''
        self.logger.debug("TimedCycleActor - On coroutine called")

        self.logger.info(f"ACTOR {self.id} ON")
        self.cbpi.notify("StepperMotorActor", f"ACTOR {self.id} ON", NotificationType.INFO)
        self.state = True

        await self.set_power(power)

    def get_state(self):
        '''
        This method is called e.g. by server functions to read the state of the actor
        '''
        self.logger.debug("TimedCycleActor - Get_state coroutine called")
        return self.state
    
    async def off(self):
        '''
        This asyncio coroutine defines what needs to be done to switch the actor off.
        '''
        self.logger.debug("TimedCycleActor - Off coroutine called")
        self.logger.info(f"ACTOR {self.id} OFF")
        GPIO.output(int(self.gpio_control), GPIO.LOW)
        self.state = False
    async def set_power(self, power):
        '''
        Dummy set_power method for testing.
        '''
        pass
    async def run(self):
        '''
        This asyncio coroutine is continuously running, while the actor is available in the system.
        '''

        self.logger.debug("TimedCycleActor - Run coroutine called")
        while self.running == True:
            if self.state == True:
                self.run_iteration()

            await asyncio.sleep(1)

    def run_iteration(self):
        self.logger.debug(f"TimedCycleActor - Run_iteration called; counter: {self.counter}")
        if self.counter == 0:
            self.logger.debug(f"TimedCycleActor: GPIO set HIGH; waiting {self.on_time} seconds")
            GPIO.output(int(self.gpio_control), GPIO.HIGH)

        elif self.counter == int(self.on_time):
            self.logger.debug(f"TimedCycleActor: GPIO set LOW; waiting for cycle to complete")
            GPIO.output(int(self.gpio_control), GPIO.LOW)

        elif self.counter == int(self.cycle_time * 60):
            self.logger.debug("TimedCycleActor: Cycle complete, resetting counter")
            self.counter = -1
        self.counter += 1