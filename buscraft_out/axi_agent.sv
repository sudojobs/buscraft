`ifndef AXI_AGENT_SV
`define AXI_AGENT_SV

`include "uvm_macros.svh"
import uvm_pkg::*;
import axi_pkg::*;

class axi_sequencer extends uvm_sequencer #(axi_txn_t);
  `uvm_component_utils(axi_sequencer)
  function new(string name = "axi_sequencer", uvm_component parent = null);
    super.new(name, parent);
  endfunction
endclass : axi_sequencer


class axi_driver extends uvm_driver #(axi_txn_t);
  `uvm_component_utils(axi_driver)
  function new(string name = "axi_driver", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual task run_phase(uvm_phase phase);
    super.run_phase(phase);
    // TODO: implement driving
  endtask
endclass : axi_driver


class axi_monitor extends uvm_component;
  `uvm_component_utils(axi_monitor)
  uvm_analysis_port #(axi_txn_t) ap;

  function new(string name = "axi_monitor", uvm_component parent = null);
    super.new(name, parent);
    ap = new("ap", this);
  endfunction

  virtual task run_phase(uvm_phase phase);
    super.run_phase(phase);
    // TODO: implement sampling
  endtask
endclass : axi_monitor


class axi_agent extends uvm_agent;

  `uvm_component_utils(axi_agent)

  axi_sequencer m_sequencer;
  axi_driver    m_driver;
  axi_monitor   m_monitor;

  function new(string name = "axi_agent", uvm_component parent = null);
    super.new(name, parent);
  endfunction : new

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (get_is_active() == UVM_ACTIVE) begin
      m_sequencer = axi_sequencer::type_id::create("m_sequencer", this);
      m_driver    = axi_driver   ::type_id::create("m_driver",    this);
    end
    m_monitor = axi_monitor::type_id::create("m_monitor", this);
  endfunction : build_phase

  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    if (get_is_active() == UVM_ACTIVE) begin
      m_driver.seq_item_port.connect(m_sequencer.seq_item_export);
    end
  endfunction : connect_phase

endclass : axi_agent

`endif // AXI_AGENT_SV