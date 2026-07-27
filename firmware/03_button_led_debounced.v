module button_led_debounced (
    input  wire clk,
    input  wire btn1,
    output reg  led1
);
    localparam DEBOUNCE_LIMIT = 60000;

    reg [16:0] counter = 0;   // needs to count up to 60000, so 17 bits (max ~131071)
    reg btn_stable = 0;

    always @(posedge clk) begin
        if (btn1 == btn_stable) begin
            counter <= 0;              // input agrees with current stable state, reset counter
        end else begin
            counter <= counter + 1;    // input disagrees -- count how long it's been different
            if (counter >= DEBOUNCE_LIMIT) begin
                btn_stable <= btn1;     // sustained long enough -- accept the new state
                counter <= 0;
            end
        end
    end

    always @(posedge clk) begin
        led1 <= btn_stable;
    end
endmodule
