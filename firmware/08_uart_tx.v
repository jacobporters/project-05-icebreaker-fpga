module uart_tx #(
    parameter CYCLES_PER_BIT = 1250   // default: 12MHz / 9600 baud
)(
    input  wire clk,
    input  wire send,        // pulse high to start a transmission
    input  wire [7:0] data,
    output reg  tx = 1'b1,   // idle high
    output reg  busy = 1'b0
);
    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state      = IDLE;
    reg [23:0] bit_timer   = 0;   // wide enough for slow AND fast versions
    reg [2:0]  bit_index   = 0;
    reg [7:0]  data_reg    = 0;

    wire tick = (bit_timer == CYCLES_PER_BIT - 1);

    always @(posedge clk) begin
        case (state)
            IDLE: begin
                tx      <= 1'b1;
                busy    <= 1'b0;
                bit_timer <= 0;
                if (send) begin
                    data_reg <= data;   // latch the byte to send
                    state    <= START;
                    busy     <= 1'b1;
                end
            end

            START: begin
                tx <= 1'b0;             // start bit
                if (tick) begin
                    bit_timer <= 0;
                    bit_index <= 0;
                    state     <= DATA;
                end else
                    bit_timer <= bit_timer + 1;
            end

            DATA: begin
                tx <= data_reg[bit_index];   // LSB first
                if (tick) begin
                    bit_timer <= 0;
                    if (bit_index == 3'd7)
                        state <= STOP;
                    else
                        bit_index <= bit_index + 1;
                end else
                    bit_timer <= bit_timer + 1;
            end

            STOP: begin
                tx <= 1'b1;             // stop bit
                if (tick) begin
                    bit_timer <= 0;
                    state     <= IDLE;
                end else
                    bit_timer <= bit_timer + 1;
            end
        endcase
    end
endmodule
