# Softwell

Pi's machine when there is no module. The program is the chip.

One cycle register. The SSD page-in advances it, each host statement advances it, and the GPU launch advances it while the CPU waits. The Pi GEMM finishes at 1,724: 421 from the SSD, 1,240 from the CPU, 63 from the GPU.

The CPU retires one Pi statement per cycle. The kernel body is not the CPU. The program is copied off the SSD at 4 bytes a cycle into 64 KB of RAM, and the bus reads that RAM. A write past the end of RAM faults.

`gpu for` is one kernel. `%tid.x` picks the thread. `pi_dot` is one product. `pi_mma` is a 4×4 tile, issued once. Tiles that fit on the 256 SMs are one wave, so the pipe runs once. A second wave pays the pipe again.

On Linux there is no `nvcuda.dll` and no Windows desktop. `gpu for`, `gpu_mm`, `gpu_seq`, `rt_gpu_seqw`, and `rt_gpu_dotmax` run here. `seqw` is `seqk` plus words, unaries, and the kernel's pruning. `dotmax` is the best f32 dot in each chunk. The device keeps 64 MB in this process: `open`, `alloc`, `put`, `get`, `copy`, and `zero`. `pi_conv`, `pi_mix`, `pi_peak`, `pi_nv12`, and the training kernels `mm`, `mm_atb`, `mm_abt`, `addbias`, `biasgrad`, relu `act`/`actb`, `mseg`, and `adam` run from `rt_gpu_launch`. `sin.approx`, `ex2.approx`, and a shader still return `-400`. `screen` is 64 by 64, `mouse` paints a pixel, `render` returns a bitmap, and `http://` uses the sockets. `https` does not. There is no Mac binary.

Each operand is written on a 32-byte bus once, then kept in 4 KB of TMEM. A shared row is not read from the bus again. A line that does not fit is dropped, oldest first, and the next use reads the bus.

The opcode is `pi.mma.block8.f32`. It is this chip's instruction, not NVIDIA's. The block is 8. The same products scored as NVFP4 blocks of 16 are the B300 column. The residual is the triangle bound, and the block of 8 still beats it on these programs.

This is not a physical bus, not a GHz, and not nvcc-clean PTX. `examples/native/gpuengine.pi` is the driver path. This directory is the machine that path is describing, written so it runs without one.

| Path | What |
|---|---|
| `src/board.ts` | CPU, RAM, SSD, the page-in |
| `src/chip.ts` | bus, the shared clock, TMEM, the PTX interpreter, the wave |
| `src/nvfp4.ts` | block-8 quantizer and the residual bound |
| `src/pi.ts` | the Pi subset that launches the chip |
| `src/samples.ts` | GEMM, attention, reduce |
| `pi/` | those programs as Pi |
