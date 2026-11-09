"""Small Modbus TCP client/server subset (FC 01/02/03/04/05/06) for local simulation."""
from __future__ import annotations
import socket, socketserver, struct, threading

class RegisterMap:
    def __init__(self): self.holding={0:220,1:80,2:1450,3:520}; self.inputs={0:0}; self.coils={0:False}; self.discrete={0:True}; self.lock=threading.RLock()
    def read(self, table, address, count):
        if not 1<=count<=125 or address<0 or address+count>65536: raise ValueError("invalid address/count")
        values=getattr(self,table)
        with self.lock:
            if any(i not in values for i in range(address,address+count)): raise ValueError("unmapped register")
            return [values[i] for i in range(address,address+count)]
    def write(self, table, address, value):
        if not 0<=address<65536 or address not in getattr(self,table): raise ValueError("unmapped address")
        with self.lock: getattr(self,table)[address]=value

def _dispatch(pdu, mapping):
    fc=pdu[0]
    if fc in (1,2,3,4):
        if len(pdu)!=5: raise ValueError("bad read request")
        addr,count=struct.unpack(">HH",pdu[1:]); table={1:"coils",2:"discrete",3:"holding",4:"inputs"}[fc]; values=mapping.read(table,addr,count)
        if fc<3:
            packed=bytearray((count+7)//8)
            for bit,value in enumerate(values): packed[bit//8] |= bool(value)<< (bit%8)
            return bytes([fc,len(packed)])+packed
        return bytes([fc,count*2])+b"".join(struct.pack(">H",v) for v in values)
    if fc in (5,6):
        if len(pdu)!=5: raise ValueError("bad write request")
        address,value=struct.unpack(">HH",pdu[1:])
        if fc==5:
            if value not in (0,0xff00): raise ValueError("invalid coil value")
            mapping.write("coils",address,value==0xff00)
        else: mapping.write("holding",address,value)
        return pdu
    raise ValueError("unsupported function code")

class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            try:
                header=self._receive(7)
                if not header: return
                tid,pid,length,unit=struct.unpack(">HHHB",header)
                if pid!=0 or not 2<=length<=254: return
                request=self._receive(length-1)
                try: response=_dispatch(request,self.server.mapping)
                except (ValueError,KeyError): response=bytes([request[0]|0x80,2])
                self.request.sendall(struct.pack(">HHHB",tid,0,len(response)+1,unit)+response)
            except (ConnectionError, OSError): return
    def _receive(self,n):
        data=b""
        while len(data)<n:
            block=self.request.recv(n-len(data))
            if not block: return b""
            data+=block
        return data

class ModbusSimulator:
    def __init__(self,host="127.0.0.1",port=0,mapping=None):
        self.mapping=mapping or RegisterMap(); self.server=socketserver.ThreadingTCPServer((host,port),_Handler); self.server.daemon_threads=True; self.server.mapping=self.mapping; self.thread=None
    @property
    def address(self): return self.server.server_address
    def __enter__(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); return self
    def __exit__(self,*_): self.server.shutdown(); self.server.server_close(); self.thread.join(2)

class ModbusClient:
    def __init__(self,host="127.0.0.1",port=502,timeout=1.0):
        if timeout<=0: raise ValueError("timeout must be positive")
        self.host,self.port,self.timeout=host,port,timeout; self._tid=0
    def request(self,pdu,unit=1):
        self._tid=(self._tid+1)&0xffff; packet=struct.pack(">HHHB",self._tid,0,len(pdu)+1,unit)+pdu
        with socket.create_connection((self.host,self.port),timeout=self.timeout) as sock:
            sock.settimeout(self.timeout); sock.sendall(packet); header=self._recv(sock,7); tid,pid,length,_=struct.unpack(">HHHB",header)
            if tid!=self._tid or pid!=0 or length<2: raise OSError("invalid Modbus TCP response header")
            response=self._recv(sock,length-1)
        if response[0]&0x80: raise OSError(f"Modbus exception response code {response[1]}")
        return response
    @staticmethod
    def _recv(sock,n):
        data=b""
        while len(data)<n:
            part=sock.recv(n-len(data))
            if not part: raise ConnectionError("Modbus peer closed connection")
            data+=part
        return data
    def read_registers(self,fc,address,count):
        if fc not in (3,4): raise ValueError("register function must be 3 or 4")
        r=self.request(bytes([fc])+struct.pack(">HH",address,count))
        if r[0]!=fc or r[1]!=count*2: raise OSError("malformed register response")
        return list(struct.unpack(">"+"H"*count,r[2:]))
    def write_register(self,address,value): self.request(b"\x06"+struct.pack(">HH",address,value))
    def read_bits(self,fc,address,count):
        if fc not in (1,2) or not 1<=count<=2000: raise ValueError("bit function must be 1 or 2 and count 1..2000")
        r=self.request(bytes([fc])+struct.pack(">HH",address,count))
        if r[0]!=fc or r[1]!=(count+7)//8: raise OSError("malformed bit response")
        return [bool(r[2+i//8] & (1<<(i%8))) for i in range(count)]
    def write_coil(self,address,value):
        if not isinstance(value,bool): raise ValueError("coil value must be boolean")
        self.request(b"\x05"+struct.pack(">HH",address,0xff00 if value else 0))

class PymodbusAdapter:
    """Optional maintained pymodbus transport for non-simulator deployments; untested here."""
    def __init__(self,host="127.0.0.1",port=502,timeout=1.0):
        try:
            from pymodbus.client import ModbusTcpClient as Client
        except ImportError as exc: raise RuntimeError("install the project dependencies to use pymodbus") from exc
        self.client=Client(host,port=port,timeout=timeout)
        if not self.client.connect(): raise ConnectionError(f"cannot connect to Modbus TCP at {host}:{port}")
    def _device_kw(self):
        import inspect
        params=inspect.signature(self.client.read_holding_registers).parameters
        return "device_id" if "device_id" in params else "slave"
    def read_holding(self,address,count,unit=1):
        response=self.client.read_holding_registers(address=address,count=count,**{self._device_kw():unit})
        if response.isError(): raise OSError(str(response))
        return response.registers
    def read_input(self,address,count,unit=1):
        response=self.client.read_input_registers(address=address,count=count,**{self._device_kw():unit})
        if response.isError(): raise OSError(str(response))
        return response.registers
    def write_holding(self,address,value,unit=1):
        response=self.client.write_register(address=address,value=value,**{self._device_kw():unit})
        if response.isError(): raise OSError(str(response))
    def close(self): self.client.close()
