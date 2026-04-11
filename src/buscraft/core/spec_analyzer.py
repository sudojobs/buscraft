"""
BusCraft Spec Analyzer — Extracts structured verification info from spec text.

Two modes:
  - FAST (default): Regex pattern matching for known protocols. No AI needed. Instant.
  - DEEP (--deep):  AI-powered analysis for unknown/custom protocols. Slower but thorough.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
import re


@dataclass
class Signal:
    """A single signal extracted from a spec."""
    name: str
    width: int = 1
    direction: str = "inout"  # "input", "output", "inout"
    description: str = ""


@dataclass
class Register:
    """A register from a register map."""
    name: str
    offset: str = "0x00"
    width: int = 32
    access: str = "RW"  # "RO", "WO", "RW", "W1C", etc.
    fields: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""


@dataclass
class TimingConstraint:
    """A timing rule or protocol constraint."""
    rule: str
    signals_involved: List[str] = field(default_factory=list)


@dataclass
class SpecModel:
    """Complete extracted specification model from an IP spec sheet."""
    ip_name: str = "unknown_ip"
    protocol_type: str = "unknown"
    description: str = ""
    
    signals: List[Signal] = field(default_factory=list)
    registers: List[Register] = field(default_factory=list)
    timing_constraints: List[TimingConstraint] = field(default_factory=list)
    
    transfer_modes: List[str] = field(default_factory=list)
    error_conditions: List[str] = field(default_factory=list)
    clock_signals: List[str] = field(default_factory=list)
    reset_signals: List[str] = field(default_factory=list)
    
    notes: List[str] = field(default_factory=list)
    protocol_confidence: float = 0.0


# =============================================================================
# FAST MODE — Pure regex, no AI, instant results
# =============================================================================

# Known protocol signal databases
KNOWN_PROTOCOLS = {
    "amba_apb": {
        "keywords": ["apb", "amba apb", "advanced peripheral bus"],
        "signals": {
            "PADDR":   {"width": 32, "direction": "output", "description": "Address bus"},
            "PSEL":    {"width": 1,  "direction": "output", "description": "Peripheral select"},
            "PENABLE": {"width": 1,  "direction": "output", "description": "Enable signal"},
            "PWRITE":  {"width": 1,  "direction": "output", "description": "Write control"},
            "PWDATA":  {"width": 32, "direction": "output", "description": "Write data bus"},
            "PRDATA":  {"width": 32, "direction": "input",  "description": "Read data bus"},
            "PREADY":  {"width": 1,  "direction": "input",  "description": "Slave ready"},
            "PSLVERR": {"width": 1,  "direction": "input",  "description": "Slave error response"},
            "PPROT":   {"width": 3,  "direction": "output", "description": "Protection type"},
            "PSTRB":   {"width": 4,  "direction": "output", "description": "Write strobe"},
        },
        "clock": "PCLK",
        "reset": "PRESETn",
        "transfer_modes": ["single"],
        "error_conditions": ["PSLVERR"],
        "timing_rules": [
            "PSEL must be asserted one cycle before PENABLE",
            "PENABLE must be asserted for exactly one cycle when PREADY is high",
            "Address and control signals must remain stable during a transfer",
        ],
    },
    "amba_axi": {
        "keywords": ["axi", "axi4", "amba axi", "advanced extensible interface"],
        "signals": {
            "AWADDR":  {"width": 32, "direction": "output", "description": "Write address"},
            "AWLEN":   {"width": 8,  "direction": "output", "description": "Burst length"},
            "AWSIZE":  {"width": 3,  "direction": "output", "description": "Burst size"},
            "AWBURST": {"width": 2,  "direction": "output", "description": "Burst type"},
            "AWVALID": {"width": 1,  "direction": "output", "description": "Write address valid"},
            "AWREADY": {"width": 1,  "direction": "input",  "description": "Write address ready"},
            "AWID":    {"width": 4,  "direction": "output", "description": "Write address ID"},
            "WDATA":   {"width": 32, "direction": "output", "description": "Write data"},
            "WSTRB":   {"width": 4,  "direction": "output", "description": "Write strobes"},
            "WLAST":   {"width": 1,  "direction": "output", "description": "Write last"},
            "WVALID":  {"width": 1,  "direction": "output", "description": "Write valid"},
            "WREADY":  {"width": 1,  "direction": "input",  "description": "Write ready"},
            "BID":     {"width": 4,  "direction": "input",  "description": "Response ID"},
            "BRESP":   {"width": 2,  "direction": "input",  "description": "Write response"},
            "BVALID":  {"width": 1,  "direction": "input",  "description": "Write response valid"},
            "BREADY":  {"width": 1,  "direction": "output", "description": "Response ready"},
            "ARADDR":  {"width": 32, "direction": "output", "description": "Read address"},
            "ARLEN":   {"width": 8,  "direction": "output", "description": "Read burst length"},
            "ARSIZE":  {"width": 3,  "direction": "output", "description": "Read burst size"},
            "ARBURST": {"width": 2,  "direction": "output", "description": "Read burst type"},
            "ARVALID": {"width": 1,  "direction": "output", "description": "Read address valid"},
            "ARREADY": {"width": 1,  "direction": "input",  "description": "Read address ready"},
            "ARID":    {"width": 4,  "direction": "output", "description": "Read address ID"},
            "RID":     {"width": 4,  "direction": "input",  "description": "Read ID"},
            "RDATA":   {"width": 32, "direction": "output", "description": "Read data"},
            "RRESP":   {"width": 2,  "direction": "input",  "description": "Read response"},
            "RLAST":   {"width": 1,  "direction": "input",  "description": "Read last"},
            "RVALID":  {"width": 1,  "direction": "input",  "description": "Read valid"},
            "RREADY":  {"width": 1,  "direction": "output", "description": "Read ready"},
        },
        "clock": "ACLK",
        "reset": "ARESETn",
        "transfer_modes": ["single", "burst", "wrap", "incr"],
        "error_conditions": ["SLVERR", "DECERR"],
        "timing_rules": [
            "VALID must not depend on READY",
            "Once VALID is asserted it must remain high until READY is asserted",
            "A master must not wait for AWREADY before asserting AWVALID",
        ],
    },
    "amba_ahb": {
        "keywords": ["ahb", "ahb-lite", "amba ahb", "advanced high-performance bus"],
        "signals": {
            "HADDR":   {"width": 32, "direction": "output", "description": "Address bus"},
            "HWDATA":  {"width": 32, "direction": "output", "description": "Write data bus"},
            "HRDATA":  {"width": 32, "direction": "input",  "description": "Read data bus"},
            "HTRANS":  {"width": 2,  "direction": "output", "description": "Transfer type"},
            "HBURST":  {"width": 3,  "direction": "output", "description": "Burst type"},
            "HSIZE":   {"width": 3,  "direction": "output", "description": "Transfer size"},
            "HWRITE":  {"width": 1,  "direction": "output", "description": "Write control"},
            "HREADY":  {"width": 1,  "direction": "input",  "description": "Transfer done"},
            "HRESP":   {"width": 2,  "direction": "input",  "description": "Transfer response"},
            "HSEL":    {"width": 1,  "direction": "output", "description": "Slave select"},
        },
        "clock": "HCLK",
        "reset": "HRESETn",
        "transfer_modes": ["single", "burst", "incr", "wrap"],
        "error_conditions": ["ERROR"],
        "timing_rules": [
            "Address phase is one clock cycle",
            "Data phase requires at least one clock cycle",
            "HTRANS must be IDLE or NONSEQ on first transfer of a burst",
        ],
    },
    "serial_i2c": {
        "keywords": ["i2c", "i c", "inter-integrated circuit"],
        "signals": {
            "SCL": {"width": 1, "direction": "inout", "description": "Serial clock"},
            "SDA": {"width": 1, "direction": "inout", "description": "Serial data"},
        },
        "clock": "clk",
        "reset": "rst_n",
        "transfer_modes": ["standard", "fast", "fast-plus"],
        "error_conditions": ["NACK"],
        "timing_rules": [
            "START condition: SDA falls while SCL is high",
            "STOP condition: SDA rises while SCL is high",
        ],
    },
}


def _detect_widths_from_text(text: str, signals: Dict) -> Dict:
    """Override default widths if the spec mentions specific bit widths."""
    updated = {}
    for sig_name, sig_info in signals.items():
        updated[sig_name] = dict(sig_info)
        # Look for patterns like "PADDR[31:0]" or "PADDR (32 bits)" or "32-bit PADDR"
        patterns = [
            rf'{sig_name}\s*\[(\d+):0\]',           # PADDR[31:0]
            rf'{sig_name}\s*\(\s*(\d+)\s*bits?\)',   # PADDR (32 bits)
            rf'(\d+)-?bit\s+{sig_name}',             # 32-bit PADDR
            rf'{sig_name}\s+(\d+)\s+bits?',          # PADDR 32 bits
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                width = int(match.group(1))
                if width > 1:
                    # [31:0] means width = 32
                    if ':' in pattern:
                        updated[sig_name]["width"] = width + 1
                    else:
                        updated[sig_name]["width"] = width
                break
    return updated


def _extract_registers_regex(text: str) -> List[Register]:
    """Extract register maps using regex patterns."""
    registers = []
    seen = set()
    
    # Pattern: 0x00 CTRL_REG RW 32 Description
    # Or: CTRL_REG (0x00) RW
    patterns = [
        r'(0x[0-9A-Fa-f]+)\s+(\w+)\s+(R[OW]|WO|RW|W1C)',
        r'(\w+_REG\w*)\s+(?:at\s+)?(0x[0-9A-Fa-f]+)',
        r'(\w+)\s*\|\s*(0x[0-9A-Fa-f]+)\s*\|\s*(\d+)\s*\|\s*(R[OW]|WO|RW|W1C)',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            if groups[0].startswith("0x"):
                offset, name = groups[0], groups[1]
                access = groups[2] if len(groups) > 2 else "RW"
            else:
                name, offset = groups[0], groups[1] if len(groups) > 1 else "0x00"
                access = groups[3] if len(groups) > 3 else "RW"
            
            if name not in seen and not name.startswith("0x"):
                registers.append(Register(name=name, offset=offset, access=access.upper()))
                seen.add(name)
    
    return registers


def analyze_spec_fast(text: str, on_progress=None) -> SpecModel:
    """Fast regex-based analysis. No AI needed. Completes in under 1 second.
    
    Works best for known protocols (APB, AXI, AHB, I2C).
    """
    spec = SpecModel()
    text_lower = text.lower()
    
    if on_progress:
        on_progress("Detecting protocol", 0, 4)
    
    # --- Step 1: Detect protocol from keywords ---
    best_protocol = None
    best_score = 0
    
    for proto_id, proto_data in KNOWN_PROTOCOLS.items():
        score = sum(1 for kw in proto_data["keywords"] if kw in text_lower)
        # Also check for signal names in the text
        signal_score = sum(1 for sig in proto_data["signals"] if sig in text)
        total = score * 2 + signal_score  # Keywords weighted higher
        
        if total > best_score:
            best_score = total
            best_protocol = proto_id
    
    if not best_protocol or best_score < 2:
        spec.notes.append("Could not detect protocol. Use --deep for AI analysis.")
        return spec
    
    proto_data = KNOWN_PROTOCOLS[best_protocol]
    
    if on_progress:
        on_progress("Extracting signals", 1, 4)
    
    # --- Step 2: Build spec model from known protocol data ---
    spec.protocol_type = best_protocol.replace("amba_", "").replace("serial_", "")
    spec.ip_name = spec.protocol_type.upper() + "_IP"
    spec.protocol_confidence = min(best_score / 10.0, 1.0)
    
    # Try to find a more specific IP name
    name_patterns = [
        r'(?:IP|module|core|block)\s+name[:\s]+(\w+)',
        r'(\w+)\s+(?:specification|datasheet|technical)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spec.ip_name = match.group(1)
            break
    
    # --- Step 3: Extract signals with width detection ---
    signals_data = _detect_widths_from_text(text, proto_data["signals"])
    
    for name, info in signals_data.items():
        # Only include signals that actually appear in the spec text
        if name in text:
            spec.signals.append(Signal(
                name=name,
                width=info["width"],
                direction=info["direction"],
                description=info["description"],
            ))
    
    # If no signals found in text, include all default signals
    if not spec.signals:
        for name, info in proto_data["signals"].items():
            spec.signals.append(Signal(
                name=name,
                width=info["width"],
                direction=info["direction"],
                description=info["description"],
            ))
    
    if on_progress:
        on_progress("Mapping registers", 2, 4)
    
    # --- Step 4: Extract registers ---
    spec.registers = _extract_registers_regex(text)
    
    # --- Step 5: Set protocol metadata ---
    spec.clock_signals = [proto_data["clock"]]
    spec.reset_signals = [proto_data["reset"]]
    spec.transfer_modes = proto_data["transfer_modes"]
    spec.error_conditions = proto_data["error_conditions"]
    
    for rule in proto_data["timing_rules"]:
        spec.timing_constraints.append(TimingConstraint(rule=rule))
    
    if on_progress:
        on_progress("Analysis complete", 4, 4)
    
    return spec


# =============================================================================
# DEEP MODE — AI-powered analysis (kept for unknown protocols)
# =============================================================================

COMBINED_EXTRACTION_PROMPT = """Extract ALL technical information from this IP specification text. Output ONLY valid JSON.

{{"ip_name": "name of the IP",
  "protocol_type": "axi|apb|ahb|chi|spi|i2c|uart|custom",
  "signals": [{{"name": "SIG_NAME", "width": 32, "direction": "input|output|inout", "description": "brief"}}],
  "registers": [{{"name": "REG_NAME", "offset": "0x00", "width": 32, "access": "RW", "description": "brief"}}],
  "timing_rules": ["rule description"],
  "transfer_modes": ["burst", "single"],
  "error_conditions": ["SLVERR"],
  "clock_signals": ["PCLK"],
  "reset_signals": ["PRESETn"],
  "confidence": 0.8}}

If a field has no data in this text, use an empty array []. Output ONLY the JSON object, nothing else.

TEXT:
{chunk}"""

# Skip patterns for irrelevant content
SKIP_PATTERNS = [
    r'table\s+of\s+contents', r'copyright\s+\d{4}', r'all\s+rights\s+reserved',
    r'revision\s+history', r'legal\s+notice', r'disclaimer', r'preface',
    r'about\s+this\s+document', r'glossary', r'list\s+of\s+figures',
]

RELEVANT_KEYWORDS = [
    'signal', 'register', 'address', 'data', 'width', 'bit', 'clock', 'reset',
    'valid', 'ready', 'enable', 'select', 'transfer', 'protocol', 'interface',
    'master', 'slave', 'bus', 'channel', 'write', 'read', 'burst', 'error',
]


def _is_relevant_chunk(chunk: str) -> bool:
    lower = chunk.lower()
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, lower) and len(chunk) < 500:
            return False
    return sum(1 for kw in RELEVANT_KEYWORDS if kw in lower) >= 2


def _safe_parse_json(text: str) -> Any:
    text = text.strip()
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r',\s*([}\]])', r'\1', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


def analyze_spec_deep(llm, chunks: List[str], on_progress=None, max_chunks: int = 6) -> SpecModel:
    """AI-powered deep analysis. Use for unknown/custom protocols."""
    relevant = [c for c in chunks if _is_relevant_chunk(c)]
    if len(relevant) > max_chunks:
        relevant = relevant[:max_chunks]
    if not relevant:
        relevant = chunks[:3]
    
    spec = SpecModel()
    total_steps = len(relevant)
    seen_signals = set()
    seen_registers = set()
    best_confidence = 0.0
    
    for i, chunk in enumerate(relevant):
        if on_progress:
            on_progress(f"AI analyzing chunk {i+1}/{total_steps}", i, total_steps)
        
        prompt = COMBINED_EXTRACTION_PROMPT.format(chunk=chunk[:3000])
        try:
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.1,
            )
            content = response["choices"][0]["message"]["content"]
            result = _safe_parse_json(content)
        except Exception:
            continue
        
        if not result or not isinstance(result, dict):
            continue
        
        confidence = float(result.get("confidence", 0.0))
        if confidence > best_confidence:
            best_confidence = confidence
            spec.ip_name = result.get("ip_name", spec.ip_name)
            spec.protocol_type = result.get("protocol_type", spec.protocol_type)
            spec.protocol_confidence = confidence
        
        for s in result.get("signals", []):
            if isinstance(s, dict) and s.get("name") and s["name"] not in seen_signals:
                spec.signals.append(Signal(
                    name=s["name"], width=int(s.get("width", 1)),
                    direction=s.get("direction", "inout"),
                    description=s.get("description", ""),
                ))
                seen_signals.add(s["name"])
        
        for r in result.get("registers", []):
            if isinstance(r, dict) and r.get("name") and r["name"] not in seen_registers:
                spec.registers.append(Register(
                    name=r["name"], offset=r.get("offset", "0x00"),
                    width=int(r.get("width", 32)), access=r.get("access", "RW"),
                    description=r.get("description", ""),
                ))
                seen_registers.add(r["name"])
        
        spec.transfer_modes.extend(result.get("transfer_modes", []))
        spec.error_conditions.extend(result.get("error_conditions", []))
        spec.clock_signals.extend(result.get("clock_signals", []))
        spec.reset_signals.extend(result.get("reset_signals", []))
        
        for rule in result.get("timing_rules", []):
            if isinstance(rule, str):
                spec.timing_constraints.append(TimingConstraint(rule=rule))
    
    spec.transfer_modes = list(set(spec.transfer_modes))
    spec.error_conditions = list(set(spec.error_conditions))
    spec.clock_signals = list(set(spec.clock_signals))
    spec.reset_signals = list(set(spec.reset_signals))
    
    if on_progress:
        on_progress("Analysis complete", total_steps, total_steps)
    
    return spec


# =============================================================================
# Main entry point — auto-selects fast vs deep mode
# =============================================================================

def analyze_spec(text_or_chunks, llm=None, on_progress=None, deep=False):
    """Analyze a spec using the fastest available method.
    
    Args:
        text_or_chunks: Full text string (fast mode) or list of chunks (deep mode).
        llm: LLM instance (only needed for deep mode).
        on_progress: Callback for progress updates.
        deep: Force AI-powered deep analysis.
    
    Returns:
        SpecModel with extracted data.
    """
    if isinstance(text_or_chunks, list):
        full_text = "\n".join(text_or_chunks)
        chunks = text_or_chunks
    else:
        full_text = text_or_chunks
        from .spec_parser import chunk_text
        chunks = chunk_text(full_text)
    
    # Try fast mode first (unless deep is forced)
    if not deep:
        spec = analyze_spec_fast(full_text, on_progress=on_progress)
        if spec.protocol_confidence > 0:
            return spec
    
    # Fall back to deep mode if fast mode couldn't detect anything
    if llm:
        return analyze_spec_deep(llm, chunks, on_progress=on_progress)
    
    # No AI available, return whatever fast mode found
    spec = analyze_spec_fast(full_text, on_progress=on_progress)
    spec.notes.append("Fast mode only — install AI model for deeper analysis.")
    return spec
