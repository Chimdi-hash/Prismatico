import pytest

# Conftest already mocks the GenLayer SDK globally
from contracts.Prismatico import Prismatico, get_block_timestamp
from tests.conftest import MockTreeMap

def test_propose_execution():
    contract = Prismatico()
    contract.boundaries = MockTreeMap()
    contract.evaluations = MockTreeMap()
    
    bid = contract.establish_boundary(
        title="Admin Ops",
        conditions="Can reboot servers but cannot delete databases.",
        delegate="0x" + "11" * 20, # Same as mock sender
        allowance=5,
        expiration_ts=get_block_timestamp() + 86400
    )
    
    # Run a proposal. Mock nondet returns "APPROVED"
    eval_id = contract.propose_execution(
        boundary_id=bid,
        request_nonce="req-123",
        execution_context="Server cluster 1",
        execution_intent="Reboot server node A"
    )
    
    assert eval_id.startswith("EVAL-")
    
    # Allowance should have decreased
    record = contract.get_boundary(bid)
    assert record["uses_remaining"] == 4
    
    evaluation = contract.get_evaluation(eval_id)
    assert evaluation["decision"] == "APPROVED"

if __name__ == '__main__':
    test_propose_execution()
    print("Consensus tests passed!")
