module baud_tick_test (
    input  wire clk,
    output reg  led1
);
    localparam CYCLES_PER_BIT = 1250;   // 12MHz / 9600 baud

    reg [10:0] bit_counter  = 0;   // needs to count to 1250 -> 11 bits (max 2047)
    reg [13:0] tick_counter = 0;   // count 9600 ticks before toggling LED

    wire bit_tick = (bit_counter == CYCLES_PER_BIT - 1);

    always @(posedge clk) begin
        if (bit_tick)
            bit_counter <= 0;
        else
            bit_counter <= bit_counter + 1;

        if (bit_tick) begin
            if (tick_counter == 9599) begin
                tick_counter <= 0;
                led1 <= ~led1;
            end else
                tick_counter <= tick_counter + 1;
        end
    end
endmodule
