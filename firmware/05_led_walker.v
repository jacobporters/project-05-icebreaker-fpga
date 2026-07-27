module led_walker (
    input  wire clk,
    output reg  led1,
    output reg  led2,
    output reg  led3,
    output reg  led4,
    output reg  led5
);
    reg [24:0] clkdiv = 0;
    wire [2:0] state = clkdiv[24:22];

    always @(posedge clk) begin
        clkdiv <= clkdiv + 1;
    end

    always @(*) begin
        case (state)
            3'd0: {led5,led4,led3,led2,led1} = 5'b00001;
            3'd1: {led5,led4,led3,led2,led1} = 5'b00010;
            3'd2: {led5,led4,led3,led2,led1} = 5'b00100;
            3'd3: {led5,led4,led3,led2,led1} = 5'b01000;
            3'd4: {led5,led4,led3,led2,led1} = 5'b10000;
            default: {led5,led4,led3,led2,led1} = 5'b00000;
        endcase
    end
endmodule
