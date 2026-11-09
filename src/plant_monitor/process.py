"""Synthetic process, register mapping, and alarm evaluation."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Limits:
    temperature_c: float = 90
    pressure_kpa: float = 600
    motor_rpm: float = 3000
    tank_percent: float = 95

def decode_registers(values):
    if len(values)!=4: raise ValueError("expected four process registers")
    decoded={"temperature_c":values[0]/10,"pressure_kpa":values[1],"motor_rpm":values[2],"tank_percent":values[3]/10}
    if not all(math.isfinite(v) and v>=0 for v in decoded.values()): raise ValueError("process values must be finite and non-negative")
    return decoded

def alarms(values,limits=Limits()):
    return [f"{name} high: {value:g} exceeds {limit:g}" for name,limit in (("temperature_c",limits.temperature_c),("pressure_kpa",limits.pressure_kpa),("motor_rpm",limits.motor_rpm),("tank_percent",limits.tank_percent)) if (value:=values[name])>limit]

def tick(mapping, step=0):
    import math
    mapping.holding.update({0:int((55+3*math.sin(step/8))*10),1:int(260+15*math.sin(step/10)),2:int(1450+80*math.sin(step/7)),3:int((62+8*math.sin(step/12))*10)})
    return decode_registers([mapping.holding[i] for i in range(4)])
