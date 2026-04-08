`ifndef BUSCRAFT_ENV_SV
`define BUSCRAFT_ENV_SV

`include "uvm_macros.svh"
import uvm_pkg::*;

// Import all protocol packages (safe even if unused)
import axi_pkg::*;
import apb_pkg::*;
import ahb_pkg::*;
import i2c_pkg::*;
import chi_pkg::*;

class buscraft_env extends uvm_env;

  `uvm_component_utils(buscraft_env)

  // Agents by protocol type
  axi_agent axi_master;

  function new(string name = "buscraft_env", uvm_component parent = null);
    super.new(name, parent);
  endfunction : new

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    axi_master = axi_agent::type_id::create("axi_master", this);
  endfunction : build_phase

endclass : buscraft_env

`endif // BUSCRAFT_ENV_SV