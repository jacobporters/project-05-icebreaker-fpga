module uart_tx_test_slow (
    input  wire clk,
    input  wire btn1,
    output wire tx,
    output wire led1,   // busy indicator
    output wire led2    // mirrors tx directly -- watch this one
);
    reg btn_prev = 1'b0;
    wire send_pulse = btn1 && !btn_prev;
    wire busy;

    uart_tx #(.CYCLES_PER_BIT(12_000_000)) tx_inst (   // 1 second per bit at 12MHz
        .clk(clk),
        .send(send_pulse),
        .data(8'h55),
        .tx(tx),
        .busy(busy)
    );

    always @(posedge clk)
        btn_prev <= btn1;

    assign led1 = busy;
    assign led2 = tx;
endmodule
