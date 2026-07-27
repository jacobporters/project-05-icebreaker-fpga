// Diagnostic-only module, not part of the design proper.
// Used to physically locate a constrained pin on the PMOD header
// by elimination: every unused floating pin on the header settles
// near 3.3V, so driving one known pin to a clean, static 0V makes
// it unambiguously identifiable against its neighbors.
module pin_finder (
    output wire tx
);
    assign tx = 1'b0;
endmodule
