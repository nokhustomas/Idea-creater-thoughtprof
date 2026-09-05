#!/bin/bash
mkdir -p sources
cd sources
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

download() {
  local fname="$1"
  local url="$2"
  curl -sL -A "$UA" -o "$fname" "$url"
  local sz=$(ls -la "$fname" 2>/dev/null | awk '{print $5}')
  local ft=$(file "$fname" 2>/dev/null | cut -d: -f2-)
  echo "$fname: $sz bytes | $ft"
}

# TechPowerUp GPU Database 静态页面
download tpu_a100.html "https://www.techpowerup.com/gpu-specs/a100-sxm4-80gb.c3506"
download tpu_rtx4090.html "https://www.techpowerup.com/gpu-specs/geforce-rtx-4090.c3889"
download wiki_a100.html "https://en.wikipedia.org/wiki/A100"
download wiki_rtx4090.html "https://en.wikipedia.org/wiki/GeForce_40_series"
download wiki_virtex.html "https://en.wikipedia.org/wiki/Virtex_UltraScale%2B"
download wiki_agilex.html "https://en.wikipedia.org/wiki/Intel_Agilex"
download wiki_llm.html "https://en.wikipedia.org/wiki/Large_language_model"
download hf_blog.html "https://huggingface.co/blog/optimize-llm"
download anaconda_transformer.html "https://www.anaconda.com/blog/transformer-fpga-inference"

# arXiv API 查 LLM FPGA 论文
download arxiv_fpga_llm.html "https://arxiv.org/search/?searchtype=all&query=FPGA+LLM+inference&start=0"
download arxiv_fpga_llm2.html "https://arxiv.org/abs/2305.12192"
download arxiv_fpga_llm3.html "https://arxiv.org/abs/2402.16408"
download arxiv_fpga_trans.html "https://arxiv.org/abs/2209.03334"

# 论文实测
download paper_fpga1.html "https://arxiv.org/abs/2309.14365"
download paper_fpga2.html "https://arxiv.org/abs/2403.08671"
download paper_fpga3.html "https://arxiv.org/abs/2208.10958"

# Xilinx 公开 datasheet
download xilinx_usp.html "https://www.xilinx.com/products/silicon-devices/fpga/virtex-ultrascale-plus/vu13p.html"

# NVIDIA LLM 推理博客
download nvidia_llm_blog.html "https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/"
download nvidia_a100_blog.html "https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/"

echo "DONE"