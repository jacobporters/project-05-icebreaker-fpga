module uart_tx_test (
    input  wire clk,
    input  wire btn1,
    output wire tx,
    output wire led1   // lit while transmitting -- sanity check even without a scope
);
    reg btn_prev = 1'b0;
    wire send_pulse = btn1 && !btn_prev;

    wire busy;

    uart_tx tx_inst (
        .clk(clk),
        .send(send_pulse),
        .data(8'h55),   // 0x55 = 01010101 -- alternating pattern, easy to verify on scope
        .tx(tx),
        .busy(busy)
    );

    always @(posedge clk)
        btn_prev <= btn1;

    assign led1 = busy;
endmodule
