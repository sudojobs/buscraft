"""Full AI Chat Panel — GUI equivalent of the CLI interactive AI mode.

Provides a chat interface backed by the local Qwen LLM with:
- Streaming responses
- Tool execution (<bash>, <read>)
- Auto file saving from code blocks
- Conversation history
- Premium chat bubble UI
"""
from __future__ import annotations
import os
import re
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox, QScrollArea, QFrame,
    QSizePolicy
)
from PySide6.QtGui import QFont, QTextCursor, QColor, QPainter, QPen
from PySide6.QtCore import Qt, QThread, Signal as QtSignal, QTimer

from buscraft.gui.theme import C, Fonts


# System prompt matching the CLI's interactive mode
SYSTEM_PROMPT = (
    "You are BusCraft AI, an autonomous UVM verification expert agent. "
    "You can control the terminal and read/write files to accomplish complex tasks.\n"
    "CRITICAL INSTRUCTIONS:\n"
    "1. Specialize in UVM environments and IEEE 1800.2 guidelines.\n"
    "2. NO conversational filler. Output only technical explanations and tool calls.\n"
    "3. AUTONOMOUS TOOLS: You have access to the following XML tools. To use one, output the exact tag. "
    "You will receive the tool output in the next message.\n"
    "   - Run terminal command: <bash> command here </bash>\n"
    "   - Read a file's content: <read> filepath here </read>\n"
    "   - Auto-write a file: Output a code block starting with // File: <filename.sv>\n"
    "4. You must ONLY use ONE <bash> or <read> tool per message. "
    "You will automatically receive the execution result in the next message to continue your thought process.\n"
)


# ── Workers ────────────────────────────────────────────────────────────────

class _LLMLoadWorker(QThread):
    """Loads the LLM model in a background thread."""
    finished = QtSignal(object)  # Llama instance or None
    error = QtSignal(str)
    status = QtSignal(str)

    def run(self):
        try:
            self.status.emit("Checking for llama-cpp-python…")
            try:
                from llama_cpp import Llama
            except ImportError:
                self.error.emit(
                    "llama-cpp-python is not installed.\n"
                    "Install with: pip install llama-cpp-python"
                )
                return

            self.status.emit("Downloading / loading Qwen 7B model (may take a while on first run)…")
            from huggingface_hub import hf_hub_download
            model_path = hf_hub_download(
                repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
                filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
            )

            self.status.emit("Initializing LLM engine (CPU mode)…")
            llm = Llama(
                model_path=model_path,
                verbose=False,
                n_ctx=2048,
                n_gpu_layers=0,
                n_threads=4,
                seed=42,
            )
            self.finished.emit(llm)
        except Exception as exc:
            self.error.emit(str(exc))


class _ChatWorker(QThread):
    """Runs a single chat completion turn with tool-use loop in background."""
    token = QtSignal(str)       # streaming token
    tool_exec = QtSignal(str)   # tool execution status message
    file_saved = QtSignal(str)  # file saved notification
    finished = QtSignal(str)    # full response text
    error = QtSignal(str)

    def __init__(self, llm, messages: list):
        super().__init__()
        self.llm = llm
        self.messages = list(messages)  # copy
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            full_response = self._run_agentic_loop()
            self.finished.emit(full_response)
        except Exception as exc:
            self.error.emit(str(exc))

    def _run_agentic_loop(self) -> str:
        """Run the agentic tool-use loop (same as CLI interactive_mode)."""
        all_responses = []

        while not self._stop:
            response_text = ""

            try:
                stream = self.llm.create_chat_completion(
                    messages=self.messages,
                    stream=True,
                    max_tokens=2048,
                    stop=["</bash>", "</read>"],
                )
                for chunk in stream:
                    if self._stop:
                        break
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        response_text += delta
                        self.token.emit(delta)
            except Exception as exc:
                self.error.emit(f"LLM error: {exc}")
                break

            # Fix unclosed tool tags
            if "<bash>" in response_text and "</bash>" not in response_text:
                response_text += "</bash>"
            if "<read>" in response_text and "</read>" not in response_text:
                response_text += "</read>"

            self.messages.append({"role": "assistant", "content": response_text})
            all_responses.append(response_text)

            # --- Auto file saves ---
            pattern = r"//\s*File:\s*([^\n]+)\s*\n.*?(```[a-zA-Z0-9_\-]*\s*\n(.*?)\n```)"
            for match in re.finditer(pattern, response_text, re.DOTALL):
                filename = match.group(1).strip()
                code_content = match.group(3).strip()
                try:
                    if os.path.dirname(filename):
                        os.makedirs(os.path.dirname(filename), exist_ok=True)
                    with open(filename, "w") as f:
                        f.write(code_content + "\n")
                    self.file_saved.emit(filename)
                except Exception as exc:
                    self.tool_exec.emit(f"Failed to save {filename}: {exc}")

            # --- Tool execution ---
            bash_match = re.search(r"<bash>(.*?)</bash>", response_text, re.DOTALL)
            read_match = re.search(r"<read>(.*?)</read>", response_text, re.DOTALL)

            if bash_match:
                cmd = bash_match.group(1).strip()
                self.tool_exec.emit(f"Executing: {cmd}")
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=30,
                    )
                    output = (result.stdout + result.stderr).strip()
                    if not output:
                        output = "Command executed successfully with no output."
                except subprocess.TimeoutExpired:
                    output = "Command timed out after 30 seconds."
                except Exception as exc:
                    output = f"Failed to execute command: {exc}"

                self.messages.append({
                    "role": "user",
                    "content": f"Tool Execution Result for <bash>{cmd}</bash>:\n{output}",
                })
                self.tool_exec.emit(f"Result fed back to AI…")
                continue  # Continue agentic loop

            elif read_match:
                filepath = read_match.group(1).strip()
                self.tool_exec.emit(f"Reading: {filepath}")
                try:
                    with open(filepath, "r") as f:
                        output = f.read()
                except Exception as exc:
                    output = f"Failed to read file: {exc}"

                self.messages.append({
                    "role": "user",
                    "content": f"Tool Execution Result for <read>{filepath}</read>:\n{output}",
                })
                self.tool_exec.emit(f"File content fed back to AI…")
                continue  # Continue agentic loop

            # No tool calls — break the loop
            break

        return "\n".join(all_responses)


# ── UI Components ──────────────────────────────────────────────────────────

class _MessageBubble(QWidget):
    """A chat message bubble (User, AI, System, or Tool)."""
    
    def __init__(self, role: str, text: str, parent=None):
        super().__init__(parent)
        self.role = role
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bubble = QWidget()
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        bubble_layout.addWidget(self.label)
        
        # Max width to prevent long lines from spanning entire screen
        self.bubble.setMaximumWidth(700)
        
        if role == "user":
            main_layout.addStretch()
            main_layout.addWidget(self.bubble)
            self.bubble.setStyleSheet(f"""
                QWidget {{
                    background: {C.PRIMARY};
                    border-radius: 12px;
                    border-top-right-radius: 4px;
                }}
                QLabel {{ 
                    color: {C.TEXT_ON_PRIMARY}; 
                    font-size: 13px; 
                    background: transparent; 
                    padding: 4px;
                }}
            """)
        elif role == "ai":
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()
            self.label.setFont(QFont("Menlo, Consolas, monospace", 11))
            self.bubble.setStyleSheet(f"""
                QWidget {{
                    background: {C.BG_ELEVATED};
                    border: 1px solid {C.BORDER};
                    border-radius: 12px;
                    border-top-left-radius: 4px;
                }}
                QLabel {{ 
                    color: {C.TEXT}; 
                    background: transparent; 
                    padding: 4px;
                }}
            """)
        elif role == "tool":
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()
            self.bubble.setStyleSheet(f"""
                QWidget {{
                    background: {C.BG_SURFACE};
                    border: 1px dashed {C.BORDER};
                    border-radius: 8px;
                }}
                QLabel {{ 
                    color: {C.TEXT_DIM}; 
                    font-family: Menlo, Consolas, monospace; 
                    font-size: 11px; 
                    background: transparent; 
                }}
            """)
        elif role == "system":
            main_layout.addStretch()
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()
            self.label.setAlignment(Qt.AlignCenter)
            self.bubble.setStyleSheet(f"""
                QWidget {{
                    background: transparent;
                }}
                QLabel {{ 
                    color: {C.TEXT_DIM}; 
                    font-size: 11px; 
                    font-style: italic;
                    background: transparent; 
                }}
            """)

    def append_text(self, text: str):
        self.label.setText(self.label.text() + text)


class AIPanel(QWidget):
    """Full AI chat panel with premium bubble interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._llm = None
        self._messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._load_worker: _LLMLoadWorker | None = None
        self._chat_worker: _ChatWorker | None = None
        self._active_ai_bubble: _MessageBubble | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # --- Header ---
        header_row = QHBoxLayout()
        title = QLabel("AI Assistant")
        title.setObjectName("pageTitle")
        header_row.addWidget(title)
        
        header_row.addStretch()
        
        self.lbl_status = QLabel("Backend: Not loaded")
        self.lbl_status.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px;")
        header_row.addWidget(self.lbl_status)
        
        header_row.addSpacing(16)
        
        self.btn_load = QPushButton("Load Local Model")
        self.btn_load.clicked.connect(self._on_load_model)
        
        self.btn_clear = QPushButton("Clear Chat")
        self.btn_clear.clicked.connect(self._on_clear)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)
        
        header_row.addWidget(self.btn_load)
        header_row.addWidget(self.btn_stop)
        header_row.addWidget(self.btn_clear)
        
        layout.addLayout(header_row)

        # --- Chat Display (Scroll Area) ---
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("background: transparent;")
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(24)
        
        # Welcome Screen
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        
        logo_label = QLabel("BusCraft AI")
        logo_label.setStyleSheet(f"color: {C.PRIMARY}; font-size: 32px; font-weight: bold; background: transparent;")
        logo_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(logo_label)
        
        sub_label = QLabel("How can I help you design your UVM environment today?")
        sub_label.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 16px; background: transparent;")
        sub_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(sub_label)
        
        welcome_layout.addSpacing(32)
        
        suggestions_layout = QHBoxLayout()
        suggestions_layout.setSpacing(16)
        
        for text in ["Generate AXI Agent", "Explain UVM Sequences", "Write APB Monitor"]:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.BG_ELEVATED};
                    border: 1px solid {C.BORDER};
                    border-radius: 16px;
                    padding: 12px 20px;
                    color: {C.TEXT};
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {C.BG_SURFACE};
                    border: 1px solid {C.PRIMARY};
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, t=text: self._on_suggestion(t))
            suggestions_layout.addWidget(btn)
            
        welcome_layout.addLayout(suggestions_layout)
        self.chat_layout.addWidget(self.welcome_widget)
        
        self.chat_layout.addStretch() # Push messages up
        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll, stretch=1)

        # --- Input ---
        input_wrapper = QHBoxLayout()
        input_wrapper.setContentsMargins(40, 0, 40, 0)
        
        input_container = QWidget()
        input_container.setMaximumWidth(800)
        input_container.setStyleSheet(f"""
            QWidget {{
                background: {C.BG_ELEVATED};
                border: 1px solid {C.BORDER};
                border-radius: 24px;
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(16, 8, 8, 8)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Message BusCraft AI...")
        self.input_field.setStyleSheet(f"border: none; background: transparent; font-size: {Fonts.BODY}px;")
        self.input_field.setMinimumHeight(40)
        self.input_field.returnPressed.connect(self._on_send)

        self.btn_send = QPushButton("Send")
        self.btn_send.setMinimumHeight(36)
        self.btn_send.setMinimumWidth(80)
        self.btn_send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRIMARY};
                color: {C.TEXT_ON_PRIMARY};
                border-radius: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:disabled {{
                background: {C.BG_SURFACE};
                color: {C.TEXT_MUTED};
            }}
        """)
        self.btn_send.clicked.connect(self._on_send)

        input_layout.addWidget(self.input_field, stretch=1)
        input_layout.addWidget(self.btn_send)
        
        input_wrapper.addStretch()
        input_wrapper.addWidget(input_container, stretch=1)
        input_wrapper.addStretch()
        layout.addLayout(input_wrapper)

    # ---------------------------------------------------------------- Model

    def _on_suggestion(self, text: str):
        self.input_field.setText(text)
        self._on_send()

    def _on_load_model(self):
        if self._llm:
            self._append_bubble("system", "AI model already loaded.")
            return

        self.btn_load.setEnabled(False)
        self._append_bubble("system", "Loading AI model…")
        self.welcome_widget.setVisible(False)

        self._load_worker = _LLMLoadWorker()
        self._load_worker.status.connect(self._on_load_status)
        self._load_worker.finished.connect(self._on_model_loaded)
        self._load_worker.error.connect(self._on_model_error)
        self._load_worker.start()

    def _on_load_status(self, msg: str):
        self.lbl_status.setText(f"Backend: {msg}")

    def _on_model_loaded(self, llm):
        self._llm = llm
        self.lbl_status.setText("Backend: Ready (Qwen 7B, CPU)")
        self._append_bubble("system", "AI model loaded successfully! You can now ask questions.")
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.btn_load.setEnabled(False)
        self.input_field.setFocus()

    def _on_model_error(self, msg: str):
        self.lbl_status.setText("Backend: Failed")
        self._append_bubble("system", f"Failed to load AI model: {msg}")
        self.btn_load.setEnabled(True)

    # ------------------------------------------------------------------ Chat

    def _add_bubble(self, role: str, text: str = "") -> _MessageBubble:
        """Add a new message bubble to the chat layout."""
        bubble = _MessageBubble(role, text)
        # Insert before the stretch at the bottom
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _append_bubble(self, role: str, text: str):
        """Add a complete bubble."""
        self._add_bubble(role, text)

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.welcome_widget.setVisible(False)
        
        if not self._llm:
            self._append_bubble("system", "Please load the AI model first using the button in the top right.")
            self.input_field.clear()
            return

        self.input_field.clear()
        self._append_bubble("user", text)

        self._messages.append({"role": "user", "content": text})

        # Disable input while generating
        self.input_field.setEnabled(False)
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # Create the active AI bubble for streaming
        self._active_ai_bubble = self._add_bubble("ai")

        self._chat_worker = _ChatWorker(self._llm, self._messages)
        self._chat_worker.token.connect(self._on_token)
        self._chat_worker.tool_exec.connect(self._on_tool_exec)
        self._chat_worker.file_saved.connect(self._on_file_saved)
        self._chat_worker.finished.connect(self._on_chat_done)
        self._chat_worker.error.connect(self._on_chat_error)
        self._chat_worker.start()

    def _on_stop(self):
        if self._chat_worker:
            self._chat_worker.stop()
        self._append_bubble("system", "Generation stopped.")
        self._re_enable_input()

    def _on_clear(self):
        # Remove all bubbles except the welcome widget and stretch
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            widget = item.widget()
            if widget and widget != self.welcome_widget:
                widget.deleteLater()
        
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.welcome_widget.setVisible(True)

    def _on_token(self, token: str):
        if self._active_ai_bubble:
            self._active_ai_bubble.append_text(token)
            # Only scroll occasionally to prevent lag
            if len(self._active_ai_bubble.label.text()) % 100 == 0:
                self._scroll_to_bottom()

    def _on_tool_exec(self, msg: str):
        self._append_bubble("tool", msg)

    def _on_file_saved(self, filepath: str):
        self._append_bubble("tool", f"Saved file: {filepath}")

    def _on_chat_done(self, full_response: str):
        # Update conversation history with the final response
        if self._chat_worker:
            self._messages = self._chat_worker.messages
        self._active_ai_bubble = None
        self._re_enable_input()
        self._scroll_to_bottom()

    def _on_chat_error(self, msg: str):
        self._append_bubble("system", f"Error: {msg}")
        self._active_ai_bubble = None
        self._re_enable_input()

    def _re_enable_input(self):
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.input_field.setFocus()
        
    def _scroll_to_bottom(self):
        """Scroll the chat view to the bottom."""
        QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
