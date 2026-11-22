# Softwell

Pi's GPU when there is no module. The program is the chip.

`gpu for` is one kernel. `%tid.x` picks the thread. `pi_dot` is one product. `pi_mma` is a 4×4 tile, issued once. Tiles that fit on the 256 SMs are one wave, so the pipe runs once. A second wave pays the pipe again.

Each operand is written on a 32-byte bus once, then kept in 4 KB of TMEM. A shared row is not read from the bus again. A line that does not fit is dropped, oldest first, and the next use reads the bus.

The opcode is `pi.mma.block8.f32`. It is this chip's instruction, not NVIDIA's. The block is 8. The same products scored as NVFP4 blocks of 16 are the B300 column. The residual is the triangle bound, and the block of 8 still beats it on these programs.

This is not a physical bus, not a GHz, and not nvcc-clean PTX. `examples/native/gpuengine.pi` is the driver path. This directory is the chip that path is describing, written so it runs without one.

| Path | What |
|---|---|
| `src/chip.ts` | bus, clock, TMEM, the PTX interpreter, the wave |
| `src/nvfp4.ts` | block-8 quantizer and the residual bound |
| `src/pi.ts` | the Pi subset that launches the chip |
| `src/samples.ts` | GEMM, attention, reduce |
| `pi/` | those programs as Pi |
