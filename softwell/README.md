# Softwell

The only GPU, CPU, SSD, and RAM Pi needs. The program is the chip.

One cycle register. The SSD page-in advances it, each host statement advances it, and the GPU launch advances it while the CPU waits. The launch's GPU time is the bytes it touches, one bus cycle per 32 bytes. It is not a separate 63-cycle GEMM.

The CPU retires one Pi statement per cycle. The kernel body is not the CPU. The program is copied off the SSD at 4 bytes a cycle into 64 KB of RAM, and the bus reads that RAM. A write past the end of RAM faults.

`gpu for` is one kernel. `%tid.x` picks the thread. `pi_dot` is one product. `pi_mma` is a 4×4 tile, issued once. Tiles that fit on the 256 SMs are one wave, so the pipe runs once. A second wave pays the pipe again.

Softwell is that machine on both hosts. RAM is 64 KB. The SSD is 1 MB, in pages of 4 KB, copied in at 4 bytes a cycle. `rt_sw_page` of 1,684 bytes is 421 cycles. The same bytes on the 32-byte bus are `ceil(1684/32) = 53` cycles, and for every `n > 0` the page-in `P = ceil(n/4)` and the bus `B = ceil(n/32)` satisfy `B ≤ P ≤ 8B`. Here `53 ≤ 421 ≤ 424`. A launch adds the bus time of the bytes it touches. `tred` leaves the sum of its floats in the 4 KB TMEM, which sits beside RAM. `srow` is a shared row: at most 1,024 floats are copied into that TMEM once, and every row reads them there, so the bus pays for the vector once. `mvf32` is the same row for float weights and double vectors: the sum is float32, then widened, and the vector is kept only when it fits. `mvq8` is Q8_0 on that row: a 34-byte block is one binary16 scale and 32 signed bytes, the products are one float32 sum, and the scale multiplies it once. `mvq4` is Q4_K on that row: 144 bytes, 256 weights, binary16 `d` and `dmin`, 6-bit scales and mins, nibbles. A group of 32 sums `q*x` and `x` in float32, then adds `(d*scale)*sum_q + (-dmin*min)*sum_x`, which matches the warp when those products fit the float32 mantissa. `mvq6` is Q6_K on that row: 210 bytes, 256 weights, a nibble plus two high bits, minus 32, times a signed scale and a binary16 `d`. Sixteen products that share a scale are one float32 sum. `mxf32` is the expert table on that row: launch row `r` is local row `r mod rpe` of expert `E[r / rpe]`, and its input is vector `(r / rpe) / xd`. The dot is the same float32 sum, and a vector already in TMEM is not read again. `mxq8` is that table with the Q8_0 dot. `mxq4` is that table with the Q4_K dot. `mxq6` is that table with the Q6_K dot. `vadd` is `Y = A + B`, one `add.rn.f64` per thread, and a thread at or past `n` does not load. `silumul` is `silu(G) * U` on that index; `silu` divides `x` by `1 + exp(-x)`, and the exp is the listing's series. `rmsn` is that vector's rms norm: float32 squares, a warp butterfly, eight float64 warp sums, then `Y = X / rms(X) * W`. The reduction is 72 bytes. `gnorm` is one head of 128, the same scale, times `silu(Z)`. `amax` returns the largest value and its first index, from a block of 1,024. `ablate` takes a percent of a direction out of a token of 2,048. `capd` writes `X - H` as float32 for the tokens on the stride. A longer row does not fit, so it is not kept, and every row reads it from the bus. An allocation past the end of RAM returns `-700`. A program past the end of the SSD returns `-800`. The audio, picture, training, and volume kernels run. A shade call and a CUDA `.shared` array, including the engine's 16 KB vector, still return `-400`.

Each operand is written on a 32-byte bus once, then kept in 4 KB of TMEM. A shared row is not read from the bus again. A vector longer than 1,024 floats is not kept at all, and every row reads it from the bus. The last vector that fit stays until a later one replaces it.

The opcode is `pi.mma.block8.f32`. It is this chip's instruction, not NVIDIA's. The block is 8. The same products scored as NVFP4 blocks of 16 are the B300 column. The residual is the triangle bound, and the block of 8 still beats it on these programs.

This is not a physical bus, not a GHz, and not nvcc-clean PTX. There is no physical GPU, CPU, SSD, or RAM behind it. `examples/native/gpuengine.pi` still names `dnet`; that launch returns `-400`. `mvf32`, `mvq8`, `mvq4`, `mvq6`, `mxf32`, `mxq8`, `mxq4`, `mxq6`, `vadd`, `silumul`, `rmsn`, `gnorm`, `amax`, `ablate`, and `capd` run. `dnet` is not run: its state is 32 by 128 by 128 doubles, 4 MB, and this RAM is 64 KB. `conv` is not run either: the kept history is 3 by 8,192 doubles, 192 KB.

| Path | What |
|---|---|
| `src/board.ts` | CPU, RAM, SSD, the page-in |
| `src/chip.ts` | bus, the shared clock, TMEM, the PTX interpreter, the wave |
| `src/nvfp4.ts` | block-8 quantizer and the residual bound |
| `src/pi.ts` | the Pi subset that launches the chip |
| `src/samples.ts` | GEMM, attention, reduce |
| `pi/` | those programs as Pi |
