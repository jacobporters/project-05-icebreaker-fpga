module fpga_messenger (
    input  wire clk,
    input  wire btn1,   // sends 0x01 -- "incoming message" / start override
    input  wire btn2,   // sends the message text + 0x00 terminator
    input  wire btn3,   // sends 0x02 -- revert override
    output wire tx,
    output wire led1   // lit while transmitting -- sanity check
);
    // ---- Edge detection on all three buttons ----
    reg btn1_prev = 0, btn2_prev = 0, btn3_prev = 0;
    wire btn1_edge = btn1 && !btn1_prev;
    wire btn2_edge = btn2 && !btn2_prev;
    wire btn3_edge = btn3 && !btn3_prev;

    always @(posedge clk) begin
        btn1_prev <= btn1;
        btn2_prev <= btn2;
        btn3_prev <= btn3;
    end

    // ---- Message ROM -- edit this to change the text ----
    localparam MSG_LEN = 16;
    function [7:0] msg_rom(input [4:0] idx);
        case (idx)
            5'd0:  msg_rom = "H";
            5'd1:  msg_rom = "E";
            5'd2:  msg_rom = "L";
            5'd3:  msg_rom = "L";
            5'd4:  msg_rom = "O";
            5'd5:  msg_rom = " ";
            5'd6:  msg_rom = "F";
            5'd7:  msg_rom = "R";
            5'd8:  msg_rom = "O";
            5'd9:  msg_rom = "M";
            5'd10: msg_rom = " ";
            5'd11: msg_rom = "F";
            5'd12: msg_rom = "P";
            5'd13: msg_rom = "G";
            5'd14: msg_rom = "A";
            5'd15: msg_rom = "!";
            default: msg_rom = " ";
        endcase
    endfunction

    // ---- uart_tx instance ----
    reg        tx_send = 0;
    reg [7:0]  tx_data = 0;
    wire       tx_busy;

    uart_tx #(.CYCLES_PER_BIT(1250)) tx_inst (
        .clk(clk),
        .send(tx_send),
        .data(tx_data),
        .tx(tx),
        .busy(tx_busy)
    );

    assign led1 = tx_busy;

    // ---- Top-level sequencing FSM ----
    localparam IDLE      = 3'd0;
    localparam SEND_BYTE = 3'd1;
    localparam WAIT_BYTE = 3'd2;
    localparam SEND_MSG  = 3'd3;
    localparam WAIT_MSG  = 3'd4;
    localparam SEND_TERM = 3'd5;
    localparam WAIT_TERM = 3'd6;

    reg [2:0] state = IDLE;
    reg [4:0] msg_idx = 0;
    reg [7:0] pending_byte = 0;

    always @(posedge clk) begin
        tx_send <= 1'b0;   // default every cycle -- only pulsed high explicitly below

        case (state)
            IDLE: begin
                if (btn1_edge) begin
                    pending_byte <= 8'h01;      // "incoming message" code
                    state        <= SEND_BYTE;
                end else if (btn3_edge) begin
                    pending_byte <= 8'h02;      // "revert" code
                    state        <= SEND_BYTE;
                end else if (btn2_edge) begin
                    msg_idx <= 0;
                    state   <= SEND_MSG;
                end
            end

            // ---- single control byte (0x01 or 0x02) ----
            SEND_BYTE: begin
                if (!tx_busy) begin
                    tx_data <= pending_byte;
                    tx_send <= 1'b1;
                    state   <= WAIT_BYTE;
                end
            end
            WAIT_BYTE: begin
                if (!tx_busy)
                    state <= IDLE;
            end

            // ---- message, byte by byte ----
            SEND_MSG: begin
                if (!tx_busy) begin
                    tx_data <= msg_rom(msg_idx);
                    tx_send <= 1'b1;
                    state   <= WAIT_MSG;
                end
            end
            WAIT_MSG: begin
                if (!tx_busy) begin
                    if (msg_idx == MSG_LEN - 1)
                        state <= SEND_TERM;
                    else begin
                        msg_idx <= msg_idx + 1;
                        state   <= SEND_MSG;
                    end
                end
            end

            SEND_TERM: begin
                if (!tx_busy) begin
                    tx_data <= 8'h00;           // "end of message text"
                    tx_send <= 1'b1;
                    state   <= WAIT_TERM;
                end
            end
            WAIT_TERM: begin
                if (!tx_busy)
                    state <= IDLE;
            end
        endcase
    end
endmodule
