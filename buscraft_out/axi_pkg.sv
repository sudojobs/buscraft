`ifndef AXI_PKG_SV
`define AXI_PKG_SV

package axi_pkg;

  import uvm_pkg::*;

  typedef struct packed {
    logic [31:0] addr;
    logic [31:0] data;
    logic        write;
  } axi_txn_t;

endpackage : axi_pkg

`endif // AXI_PKG_SV