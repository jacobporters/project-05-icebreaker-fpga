module led_counter (
    input  wire clk,
    output wire led1,
    output wire led2,
    output wire led3,
    output wire led4,
    output wire led5
);
    reg [27:0] clkdiv = 0;

    always @(posedge clk) begin
        clkdiv <= clkdiv + 1;
    end

    // Slow the visible count down enough to actually watch it
    wire [4:0] count = clkdiv[27:23];

    assign led1 = count[0];
    assign led2 = count[1];
    assign led3 = count[2];
    assign led4 = count[3];
    assign led5 = count[4];
endmodule
