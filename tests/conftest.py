import sys
from pathlib import Path

# Mock GenLayer SDK so the files can be imported for basic syntax checking
class MockVM:
    class UserError(Exception): pass
    def run_nondet(self, leader, validator):
        return leader()

class MockMessage:
    def __init__(self):
        self.sender_address = "0x" + "11" * 20
        self.raw = {"datetime": "2026-09-22T12:00:00Z"}

class MockNondet:
    def exec_prompt(self, prompt, response_format):
        return {"decision": "APPROVED"}

class MockContract:
    class Contract: pass

class MockTypes:
    u256 = int

class MockTreeMap(dict):
    def get(self, k, default=None):
        return super().get(k, default)

class MockGenLayer:
    def __init__(self):
        self.vm = MockVM()
        self.message = MockMessage()
        self.nondet = MockNondet()
        self.contract = MockContract()
        self.types = MockTypes()
        
        # Mock @gl.public.write
        class Public:
            def write(self, fn): return fn
            def view(self, fn): return fn
        self.public = Public()

sys.modules['genlayer'] = MockGenLayer()
sys.modules['genlayer.types'] = MockTypes()
sys.modules['genlayer.storage'] = type("MockStorage", (), {"TreeMap": MockTreeMap})
