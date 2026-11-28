// Sigil MAC: top 40 bits of SipHash-2-4 (128-bit key) over an 11-byte little-endian body.
// sipround  : one SipRound (the iterative design reuses it for 8 cycles).
// sipmac    : fully unrolled combinational version (8 SipRounds).
module sipround(input [255:0] s, output [255:0] o);
  wire [63:0] a0 = s[63:0], a1 = s[127:64], a2 = s[191:128], a3 = s[255:192];
  wire [63:0] b0 = a0 + a1;
  wire [63:0] c1 = {a1[50:0], a1[63:51]} ^ b0;            // rotl 13
  wire [63:0] c0 = {b0[31:0], b0[63:32]};                  // rotl 32
  wire [63:0] b2 = a2 + a3;
  wire [63:0] c3 = {a3[47:0], a3[63:48]} ^ b2;            // rotl 16
  wire [63:0] d0 = c0 + c3;
  wire [63:0] d3 = {c3[42:0], c3[63:43]} ^ d0;            // rotl 21
  wire [63:0] d2 = b2 + c1;
  wire [63:0] d1 = {c1[46:0], c1[63:47]} ^ d2;            // rotl 17
  wire [63:0] e2 = {d2[31:0], d2[63:32]};                  // rotl 32
  assign o = {d3, e2, d1, d0};
endmodule

module sipmac(input [127:0] key, input [87:0] body, output [39:0] mac);
  wire [63:0] k0 = key[63:0], k1 = key[127:64];
  wire [63:0] m1 = body[63:0];
  wire [63:0] m2 = {8'd11, 32'd0, body[87:64]};                  // length byte 11 | the last 3 body bytes
  wire [255:0] s0 = {k1 ^ 64'h7465646279746573, k0 ^ 64'h6C7967656E657261, k1 ^ 64'h646F72616E646F6D, k0 ^ 64'h736F6D6570736575};
  wire [255:0] s1 = {s0[255:192] ^ m1, s0[191:0]};
  wire [255:0] r1, r2, r3, r4, r5, r6, r7, r8;
  sipround u1(s1, r1); sipround u2(r1, r2);
  wire [255:0] s2 = {r2[255:192] ^ m2, r2[191:64], r2[63:0] ^ m1};
  sipround u3(s2, r3); sipround u4(r3, r4);
  wire [255:0] s3 = {r4[255:192], r4[191:128] ^ 64'hFF, r4[127:64], r4[63:0] ^ m2};
  sipround u5(s3, r5); sipround u6(r5, r6); sipround u7(r6, r7); sipround u8(r7, r8);
  wire [63:0] t = r8[63:0] ^ r8[127:64] ^ r8[191:128] ^ r8[255:192];
  assign mac = t[63:24];
endmodule
