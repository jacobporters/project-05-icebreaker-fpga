module blinky (
    input  wire clk,
    output wire led1
);
    reg [23:0] counter = 0;

    always @(posedge clk) begin
        counter <= counter + 1;
    end

    assign led1 = counter[23];  // ~0.7 Hz blink at 12MHz
endmodule
