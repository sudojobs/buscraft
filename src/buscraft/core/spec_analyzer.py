"""
BusCraft Spec Analyzer — Uses the local LLM to extract structured
verification-relevant information from spec text chunks.

Optimized for speed: single-pass analysis with combined prompts,
junk filtering, and limited chunk count.
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
    protocol_type: str = "unknown"  # "axi", "apb", "ahb", "spi", "i2c", "custom"
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


# --- Skip patterns for irrelevant content ---
SKIP_PATTERNS = [
    r'table\s+of\s+contents',
    r'copyright\s+\d{4}',
    r'all\s+rights\s+reserved',
    r'confidential',
    r'revision\s+history',
    r'change\s+history',
    r'legal\s+notice',
    r'disclaimer',
    r'preface',
    r'about\s+this\s+document',
    r'glossary',
    r'list\s+of\s+figures',
    r'list\s+of\s+tables',
    r'appendix',
]

# Keywords that indicate a chunk is worth analyzing
RELEVANT_KEYWORDS = [
    'signal', 'register', 'address', 'data', 'width', 'bit',
    'clock', 'reset', 'valid', 'ready', 'enable', 'select',
    'transfer', 'transaction', 'protocol', 'interface', 'port',
    'master', 'slave', 'bus', 'channel', 'response', 'request',
    'write', 'read', 'strobe', 'burst', 'error', 'timeout',
    'handshake', 'phase', 'state', 'idle', 'setup', 'access',
    'psel', 'penable', 'pwrite', 'paddr', 'pwdata', 'prdata',
    'awaddr', 'wdata', 'bresp', 'araddr', 'rdata',
    'haddr', 'hwdata', 'hrdata', 'htrans',
]


def _is_relevant_chunk(chunk: str) -> bool:
    """Quickly check if a chunk contains verification-relevant content."""
    lower = chunk.lower()
    
    # Skip if it matches junk patterns
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, lower):
            # Only skip if the chunk is MOSTLY junk (short or dominated by boilerplate)
            if len(chunk) < 500:
                return False
    
    # Keep if it contains technical keywords
    keyword_count = sum(1 for kw in RELEVANT_KEYWORDS if kw in lower)
    return keyword_count >= 2


# --- Single combined prompt for speed ---

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


def _safe_parse_json(text: str) -> Any:
    """Attempt to parse JSON from LLM output, handling common formatting issues."""
    text = text.strip()
    
    # Try to extract JSON from markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    
    # Find the first { and last }
    start = text.find('{')
    end = text.rfind('}')
    
    if start >= 0 and end > start:
        text = text[start:end + 1]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to fix common issues: trailing commas
        text = re.sub(r',\s*([}\]])', r'\1', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


def analyze_chunk_combined(llm, chunk: str) -> Dict[str, Any]:
    """Extract everything from a single chunk in ONE LLM call."""
    prompt = COMBINED_EXTRACTION_PROMPT.format(chunk=chunk[:3000])  # Cap chunk size
    
    try:
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
        
        content = response["choices"][0]["message"]["content"]
        parsed = _safe_parse_json(content)
        
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    
    return {}


def analyze_spec(llm, chunks: List[str], on_progress=None, max_chunks: int = 8) -> SpecModel:
    """Run single-pass analysis on filtered spec chunks.
    
    Optimizations over multi-pass:
      - Filters out irrelevant chunks (TOC, legal, glossary)
      - Uses ONE combined prompt per chunk (was 3 separate calls)
      - Caps at max_chunks most relevant chunks
    
    Args:
        llm: The loaded llama-cpp-python model instance.
        chunks: List of text chunks from spec_parser.chunk_text().
        on_progress: Optional callback(stage: str, current: int, total: int).
        max_chunks: Maximum chunks to analyze (default 8 for speed).
    
    Returns:
        Merged SpecModel with all extracted data.
    """
    # Filter to only relevant chunks
    relevant = [c for c in chunks if _is_relevant_chunk(c)]
    
    # Cap the number of chunks to analyze
    if len(relevant) > max_chunks:
        relevant = relevant[:max_chunks]
    
    if not relevant:
        # Fallback: use first few chunks if nothing passed the filter
        relevant = chunks[:3]
    
    spec = SpecModel()
    total_steps = len(relevant)
    seen_signals = set()
    seen_registers = set()
    best_confidence = 0.0
    
    for i, chunk in enumerate(relevant):
        if on_progress:
            on_progress(f"Chunk {i+1}/{total_steps}", i, total_steps)
        
        result = analyze_chunk_combined(llm, chunk)
        if not result:
            continue
        
        # --- Merge protocol info (highest confidence wins) ---
        confidence = float(result.get("confidence", 0.0))
        if confidence > best_confidence:
            best_confidence = confidence
            spec.ip_name = result.get("ip_name", spec.ip_name)
            spec.protocol_type = result.get("protocol_type", spec.protocol_type)
            spec.protocol_confidence = confidence
        
        # --- Merge signals ---
        for s in result.get("signals", []):
            if isinstance(s, dict) and s.get("name"):
                name = s["name"]
                if name not in seen_signals:
                    spec.signals.append(Signal(
                        name=name,
                        width=int(s.get("width", 1)),
                        direction=s.get("direction", "inout"),
                        description=s.get("description", ""),
                    ))
                    seen_signals.add(name)
        
        # --- Merge registers ---
        for r in result.get("registers", []):
            if isinstance(r, dict) and r.get("name"):
                name = r["name"]
                if name not in seen_registers:
                    spec.registers.append(Register(
                        name=name,
                        offset=r.get("offset", "0x00"),
                        width=int(r.get("width", 32)),
                        access=r.get("access", "RW"),
                        description=r.get("description", ""),
                    ))
                    seen_registers.add(name)
        
        # --- Accumulate lists ---
        spec.transfer_modes.extend(result.get("transfer_modes", []))
        spec.error_conditions.extend(result.get("error_conditions", []))
        spec.clock_signals.extend(result.get("clock_signals", []))
        spec.reset_signals.extend(result.get("reset_signals", []))
        
        for rule in result.get("timing_rules", []):
            if isinstance(rule, str):
                spec.timing_constraints.append(TimingConstraint(rule=rule))
            elif isinstance(rule, dict):
                spec.timing_constraints.append(TimingConstraint(
                    rule=rule.get("rule", str(rule)),
                    signals_involved=rule.get("signals", []),
                ))
    
    # Deduplicate lists
    spec.transfer_modes = list(set(spec.transfer_modes))
    spec.error_conditions = list(set(spec.error_conditions))
    spec.clock_signals = list(set(spec.clock_signals))
    spec.reset_signals = list(set(spec.reset_signals))
    
    if on_progress:
        on_progress("Analysis complete", total_steps, total_steps)
    
    return spec
