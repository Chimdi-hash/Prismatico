import pytest

# Conftest already mocks the GenLayer SDK globally
from contracts.Prismatico import Prismatico, get_block_timestamp
from tests.conftest import MockTreeMap

def test_initialization():
    contract = Prismatico()
    contract.boundaries = MockTreeMap()
    contract.evaluations = MockTreeMap()
    
    assert contract.boundary_nonce == 0
    assert contract.eval_nonce == 0

def test_establish_boundary():
    contract = Prismatico()
    contract.boundaries = MockTreeMap()
    contract.evaluations = MockTreeMap()
    
    bid = contract.establish_boundary(
        title="Admin Ops",
        conditions="Can reboot servers but cannot delete databases.",
        delegate="0x" + "22" * 20,
        allowance=5,
        expiration_ts=get_block_timestamp() + 86400
    )
    
    assert bid.startswith("PRSM-")
    
    record = contract.get_boundary(bid)
    assert record["title"] == "Admin Ops"
    assert record["allowance"] == 5
    assert record["uses_remaining"] == 5
    assert record["is_terminated"] is False

def test_terminate_boundary():
    contract = Prismatico()
    contract.boundaries = MockTreeMap()
    contract.evaluations = MockTreeMap()
    
    bid = contract.establish_boundary(
        title="Admin Ops",
        conditions="Can reboot servers.",
        delegate="0x" + "22" * 20,
        allowance=5,
        expiration_ts=get_block_timestamp() + 86400
    )
    
    contract.terminate_boundary(bid)
    record = contract.get_boundary(bid)
    assert record["is_terminated"] is True

if __name__ == '__main__':
    test_initialization()
    test_establish_boundary()
    test_terminate_boundary()
    print("Core tests passed!")
