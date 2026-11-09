import unittest
from plant_monitor.modbus import ModbusClient,ModbusSimulator
from plant_monitor.process import Limits,alarms,decode_registers,tick

class ModbusTests(unittest.TestCase):
    def test_tcp_reads_input_and_holding_and_write(self):
        with ModbusSimulator() as server:
            client=ModbusClient(*server.address)
            self.assertEqual(client.read_registers(3,0,4),[220,80,1450,520])
            self.assertEqual(client.read_registers(4,0,1),[0])
            client.write_register(1,333)
            self.assertEqual(client.read_registers(3,1,1),[333])
            self.assertEqual(client.read_bits(1,0,1),[False])
            client.write_coil(0,True)
            self.assertEqual(client.read_bits(1,0,1),[True])
            self.assertEqual(client.read_bits(2,0,1),[True])
    def test_process_values_and_alarm_threshold(self):
        with ModbusSimulator() as server:
            client=ModbusClient(*server.address); tick(server.mapping,4)
            values=decode_registers(client.read_registers(3,0,4))
            self.assertGreater(values["temperature_c"],0)
            self.assertEqual(alarms({**values,"pressure_kpa":501},Limits(90,500,3000,95)),["pressure_kpa high: 501 exceeds 500"])
    def test_bad_count_and_timeout_rejected(self):
        with self.assertRaises(ValueError): decode_registers([1])
        with self.assertRaises(ValueError): ModbusClient(timeout=0)
