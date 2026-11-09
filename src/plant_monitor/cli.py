import argparse, json
from .modbus import ModbusClient,ModbusSimulator
from .process import tick,decode_registers,alarms

def main():
    p=argparse.ArgumentParser(description="Read simulated PLC registers through Modbus TCP"); p.add_argument("--samples",type=int,default=5); a=p.parse_args()
    if a.samples<1: p.error("samples must be positive")
    with ModbusSimulator() as server:
        client=ModbusClient(*server.address)
        for i in range(a.samples):
            tick(server.mapping,i); values=decode_registers(client.read_registers(3,0,4))
            print(json.dumps({"sample":i,"source":"simulator","values":values,"alarms":alarms(values)}))

if __name__=="__main__": main()
