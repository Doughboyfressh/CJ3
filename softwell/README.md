# Softwell

The only GPU, CPU, SSD, and RAM Pi needs. The program is the chip.

One cycle register. The SSD page-in advances it, each host statement advances it, and the GPU launch advances it while the CPU waits. The launch's GPU time is the bytes it touches, one bus cycle per 32 bytes. It is not a separate 63-cycle GEMM.

The CPU retires one Pi statement per cycle. The kernel body is not the CPU. The program is copied off the SSD at 4 bytes a cycle into 64 KB of RAM, and the bus reads that RAM. A write past the end of RAM faults.

`gpu for` is one kernel. `%tid.x` picks the thread. `pi_dot` is one product. `pi_mma` is a 4×4 tile, issued once. Tiles that fit on the 256 SMs are one wave, so the pipe runs once. A second wave pays the pipe again.

Softwell is that machine on both hosts. RAM is 64 KB. The SSD is 1 MB, in pages of 4 KB, copied in at 4 bytes a cycle. `rt_sw_page` of 1,684 bytes is 421 cycles. The same bytes on the 32-byte bus are `ceil(1684/32) = 53` cycles, and for every `n > 0` the page-in `P = ceil(n/4)` and the bus `B = ceil(n/32)` satisfy `B ≤ P ≤ 8B`. Here `53 ≤ 421 ≤ 424`. A launch adds the bus time of the bytes it touches. `tred` leaves the sum of its floats in the 4 KB TMEM, which sits beside RAM. `srow` is a shared row: at most 1,024 floats are copied into that TMEM once, and every row reads them there, so the bus pays for the vector once. `mvf32` is the same row for float weights and double vectors: the sum is float32, then widened, and the vector is kept only when it fits. `mvq8` is Q8_0 on that row: a 34-byte block is one binary16 scale and 32 signed bytes, the products are one float32 sum, and the scale multiplies it once. A longer row does not fit, so it is not kept, and every row reads it from the bus. An allocation past the end of RAM returns `-700`. A program past the end of the SSD returns `-800`. The audio, picture, training, and volume kernels run. A shade call and a CUDA `.shared` array, including the engine's 16 KB vector, still return `-400`.

Each operand is written on a 32-byte bus once, then kept in 4 KB of TMEM. A shared row is not read from the bus again. A vector longer than 1,024 floats is not kept at all, and every row reads it from the bus. The last vector that fit stays until a later one replaces it.

The opcode is `pi.mma.block8.f32`. It is this chip's instruction, not NVIDIA's. The block is 8. The same products scored as NVFP4 blocks of 16 are the B300 column. The residual is the triangle bound, and the block of 8 still beats it on these programs.

This is not a physical bus, not a GHz, and not nvcc-clean PTX. There is no physical GPU, CPU, SSD, or RAM behind it. `examples/native/gpuengine.pi` still names `mvq4`, `mvq6`, the expert-table kernels, and `dnet`; those launches return `-400`. `mvf32` and `mvq8` run.

| Path | What |
|---|---|
| `src/board.ts` | CPU, RAM, SSD, the page-in |
| `src/chip.ts` | bus, the shared clock, TMEM, the PTX interpreter, the wave |
| `src/nvfp4.ts` | block-8 quantizer and the residual bound |
| `src/pi.ts` | the Pi subset that launches the chip |
| `src/samples.ts` | GEMM, attention, reduce |
| `pi/` | those programs as Pi |
