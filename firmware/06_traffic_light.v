module traffic_light (
    input  wire clk,
    output reg  led1,  // red
    output reg  led2,  // yellow
    output reg  led3   // green
);
    // Named states instead of raw numbers -- self-documenting
    localparam RED    = 2'd0;
    localparam GREEN  = 2'd1;
    localparam YELLOW = 2'd2;

    reg [1:0]  state   = RED;
    reg [25:0] counter = 0;

    // Durations in clock cycles at 12MHz
    localparam RED_TIME    = 26'd48_000_000; // 4s
    localparam GREEN_TIME  = 26'd48_000_000; // 4s
    localparam YELLOW_TIME = 26'd12_000_000; // 1s

    // Block 1: state transitions + timing (sequential)
    always @(posedge clk) begin
        case (state)
            RED: begin
                if (counter >= RED_TIME) begin
                    state   <= GREEN;
                    counter <= 0;
                end else
                    counter <= counter + 1;
            end
            GREEN: begin
                if (counter >= GREEN_TIME) begin
                    state   <= YELLOW;
                    counter <= 0;
                end else
                    counter <= counter + 1;
            end
            YELLOW: begin
                if (counter >= YELLOW_TIME) begin
                    state   <= RED;
                    counter <= 0;
                end else
                    counter <= counter + 1;
            end
            default: begin
                state   <= RED;
                counter <= 0;
            end
        endcase
    end

    // Block 2: outputs, purely a function of current state (combinational)
    always @(*) begin
        led1 = (state == RED);
        led2 = (state == YELLOW);
        led3 = (state == GREEN);
    end
endmodule
