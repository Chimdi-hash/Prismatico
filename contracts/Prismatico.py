# v1.0.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import hashlib
import re
from typing import NoReturn
from genlayer import *

# --- Constants & Limits ---
VERSION = "Prismatico/1.0"

DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"
DECISION_AMBIGUOUS = "AMBIGUOUS"
VALID_DECISIONS = (DECISION_APPROVED, DECISION_REJECTED, DECISION_AMBIGUOUS)

STATE_ACTIVE = "ACTIVE"
STATE_TERMINATED = "TERMINATED"
STATE_DEPLETED = "DEPLETED"
STATE_EXPIRED = "EXPIRED"

STR_LIMIT_TITLE = 200
STR_LIMIT_CONDITIONS = 5000
STR_LIMIT_NONCE = 128
STR_LIMIT_CONTEXT = 3000
STR_LIMIT_INTENT = 4000
MAX_JSON_BYTES = 20000


# --- Helpers ---
def throw_error(reason: str, detail: str) -> NoReturn:
    raise gl.vm.UserError(f"[{reason}] {detail}")

def enforce_text(val: str, max_bytes: int, field_name: str, allow_empty: bool = False) -> str:
    if not isinstance(val, str):
        throw_error("VALIDATION_ERROR", f"Field '{field_name}' must be a string.")
    if not allow_empty and not val.strip():
        throw_error("VALIDATION_ERROR", f"Field '{field_name}' cannot be empty.")
    try:
        byte_length = len(val.encode('utf-8'))
    except UnicodeEncodeError:
        throw_error("VALIDATION_ERROR", f"Field '{field_name}' has invalid encoding.")
    if byte_length > max_bytes:
        throw_error("VALIDATION_ERROR", f"Field '{field_name}' exceeds {max_bytes} bytes limit.")
    return val

def enforce_address(addr: str) -> str:
    if not isinstance(addr, str) or not addr.startswith("0x") or len(addr) != 42:
        throw_error("VALIDATION_ERROR", "Address must be a 42-character hex string starting with 0x.")
    addr_lower = addr.lower()
    if addr_lower == "0x" + "0" * 40:
        throw_error("VALIDATION_ERROR", "Zero address is not permitted.")
    return addr_lower

def get_caller() -> str:
    return enforce_address(str(gl.message.sender_address))

def serialize_json(data: dict) -> str:
    res = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(res.encode('utf-8')) > MAX_JSON_BYTES:
        throw_error("CAPACITY_ERROR", "Serialized data exceeds maximum allowed size.")
    return res

def create_hash(prefix: str, payload: dict) -> str:
    raw = f"{VERSION}|{prefix}|{serialize_json(payload)}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def get_block_timestamp() -> int:
    try:
        dt_str = gl.message.raw["datetime"]
        # Basic parsing of UTC ISO string like '2026-09-22T12:00:00Z'
        if not isinstance(dt_str, str):
            raise ValueError()
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        elif dt_str.endswith("+00:00"):
            dt_str = dt_str[:-6]
        
        date_part, time_part = dt_str.split("T")
        y, m, d = map(int, date_part.split("-"))
        h, mn, s = map(int, time_part.split(".")[0].split(":"))
        
        # Approximate epoch calculation
        days = d - 1
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        for i in range(m - 1):
            days += month_days[i]
            if i == 1 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
                days += 1
        days += (y - 1970) * 365 + (y - 1969) // 4 - (y - 1901) // 100 + (y - 1601) // 400
        return days * 86400 + h * 3600 + mn * 60 + s
    except Exception:
        throw_error("TIME_ERROR", "Unable to securely parse transaction timestamp.")

# --- Core Contract ---
class Prismatico(gl.Contract):
    # Storage maps
    boundaries: TreeMap[str, str]
    evaluations: TreeMap[str, str]
    
    # Counters
    boundary_nonce: u256
    eval_nonce: u256

    def __init__(self):
        self.boundary_nonce = 0
        self.eval_nonce = 0

    # --- View Methods ---
    
    @gl.public.view
    def get_boundary(self, boundary_id: str) -> dict:
        data = self.boundaries.get(boundary_id, "")
        if not data:
            throw_error("NOT_FOUND", "Boundary does not exist.")
        return json.loads(data)

    @gl.public.view
    def get_evaluation(self, eval_id: str) -> dict:
        data = self.evaluations.get(eval_id, "")
        if not data:
            throw_error("NOT_FOUND", "Evaluation does not exist.")
        return json.loads(data)

    @gl.public.view
    def get_boundary_state(self, boundary_id: str) -> str:
        bnd = self.get_boundary(boundary_id)
        if bnd["is_terminated"]:
            return STATE_TERMINATED
        if bnd["uses_remaining"] <= 0:
            return STATE_DEPLETED
        if get_block_timestamp() >= bnd["expiration_ts"]:
            return STATE_EXPIRED
        return STATE_ACTIVE

    # --- Write Methods ---

    @gl.public.write
    def establish_boundary(self, title: str, conditions: str, delegate: str, allowance: u256, expiration_ts: u256) -> str:
        creator = get_caller()
        title = enforce_text(title, STR_LIMIT_TITLE, "title")
        conditions = enforce_text(conditions, STR_LIMIT_CONDITIONS, "conditions")
        delegate = enforce_address(delegate)
        
        if allowance <= 0:
            throw_error("VALIDATION_ERROR", "Allowance must be at least 1.")
        
        current_time = get_block_timestamp()
        if expiration_ts <= current_time:
            throw_error("VALIDATION_ERROR", "Expiration time must be in the future.")
            
        self.boundary_nonce += 1
        seq = self.boundary_nonce
        
        boundary_id = "PRSM-" + create_hash("id", {"seq": seq, "creator": creator, "ts": current_time})
        
        record = {
            "id": boundary_id,
            "creator": creator,
            "delegate": delegate,
            "title": title,
            "conditions": conditions,
            "allowance": allowance,
            "uses_remaining": allowance,
            "creation_ts": current_time,
            "expiration_ts": expiration_ts,
            "is_terminated": False
        }
        
        self.boundaries[boundary_id] = serialize_json(record)
        return boundary_id

    @gl.public.write
    def terminate_boundary(self, boundary_id: str):
        caller = get_caller()
        bnd = self.get_boundary(boundary_id)
        if bnd["creator"] != caller:
            throw_error("ACCESS_DENIED", "Only the creator can terminate this boundary.")
        if bnd["is_terminated"]:
            throw_error("LIFECYCLE", "Boundary is already terminated.")
            
        bnd["is_terminated"] = True
        self.boundaries[boundary_id] = serialize_json(bnd)

    @gl.public.write
    def propose_execution(self, boundary_id: str, request_nonce: str, execution_context: str, execution_intent: str) -> str:
        caller = get_caller()
        bnd = self.get_boundary(boundary_id)
        
        if caller != bnd["delegate"]:
            throw_error("ACCESS_DENIED", "Only the designated delegate can propose executions.")
            
        state = self.get_boundary_state(boundary_id)
        if state != STATE_ACTIVE:
            throw_error("LIFECYCLE", f"Cannot execute. Boundary state is {state}.")
            
        request_nonce = enforce_text(request_nonce, STR_LIMIT_NONCE, "request_nonce")
        execution_context = enforce_text(execution_context, STR_LIMIT_CONTEXT, "execution_context", allow_empty=True)
        execution_intent = enforce_text(execution_intent, STR_LIMIT_INTENT, "execution_intent")
        
        eval_id = "EVAL-" + create_hash("eval_id", {
            "boundary": boundary_id,
            "nonce": request_nonce,
            "caller": caller
        })
        
        if self.evaluations.get(eval_id, "") != "":
            throw_error("REPLAY", "This request nonce has already been processed.")
            
        snapshot = {
            "title": bnd["title"],
            "conditions": bnd["conditions"],
            "context": execution_context,
            "intent": execution_intent
        }
        
        decision = self._reach_consensus(snapshot)
        
        if decision == DECISION_APPROVED:
            bnd["uses_remaining"] -= 1
            self.boundaries[boundary_id] = serialize_json(bnd)
            
        self.eval_nonce += 1
        
        eval_record = {
            "eval_id": eval_id,
            "boundary_id": boundary_id,
            "delegate": caller,
            "nonce": request_nonce,
            "context": execution_context,
            "intent": execution_intent,
            "decision": decision,
            "timestamp": get_block_timestamp()
        }
        
        self.evaluations[eval_id] = serialize_json(eval_record)
        return eval_id

    # --- Consensus Logic ---

    def _build_prompt(self, snapshot: dict) -> str:
        return (
            "You are the deterministic semantic evaluator for the Prismatico capability system.\n"
            "Your task is to evaluate a proposed intent against a set of strictly defined conditions.\n\n"
            "=== BOUNDARY DEFINITION ===\n"
            f"TITLE: {snapshot['title']}\n"
            f"CONDITIONS: {snapshot['conditions']}\n\n"
            "=== EXECUTION PROPOSAL ===\n"
            f"CONTEXT: {snapshot['context']}\n"
            f"INTENT: {snapshot['intent']}\n\n"
            "EVALUATION RULES:\n"
            "1. You must answer if the INTENT strictly adheres to all constraints in the CONDITIONS.\n"
            "2. If the INTENT violates any restriction, output REJECTED.\n"
            "3. If the INTENT is fully permitted, output APPROVED.\n"
            "4. If there is ambiguity, missing information, or contradiction, output AMBIGUOUS.\n"
            "Respond ONLY with a valid JSON object containing exactly one key 'decision' with value APPROVED, REJECTED, or AMBIGUOUS."
        )

    def _query_model(self, snapshot: dict) -> str:
        prompt = self._build_prompt(snapshot)
        raw_response = gl.nondet.exec_prompt(prompt, response_format="json")
        
        if not isinstance(raw_response, dict) or "decision" not in raw_response:
            throw_error("LLM_ERROR", "Invalid response format from model.")
            
        decision = raw_response["decision"]
        if decision not in VALID_DECISIONS:
            throw_error("LLM_ERROR", f"Model returned invalid decision: {decision}")
            
        return decision

    def _reach_consensus(self, snapshot: dict) -> str:
        def leader_logic():
            return self._query_model(snapshot)
            
        def validator_logic(leader_output) -> bool:
            if not isinstance(leader_output, gl.vm.Return):
                return False
            try:
                local_decision = self._query_model(snapshot)
                return leader_output.calldata == local_decision
            except Exception:
                return False
                
        return gl.vm.run_nondet(leader_logic, validator_logic)
