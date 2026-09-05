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

download a100.html "https://www.nvidia.com/en-us/data-center/a100/"
download a100_datasheet.pdf "https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/a100-datasheet-us-nvidia-1758950-r4-web.pdf"
download a100_tech_overview.pdf "https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/Ampere-Architecture-Whitepaper.pdf"
download rtx4090.html "https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/"
download rtx4090_pb.html "https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/specifications/"
download vu13p.html "https://www.xilinx.com/products/silicon-devices/fpga/virtex-ultrascale-plus.html"
download vu13p_ds.pdf "https://docs.xilinx.com/v/u/en-US/ds890-ultrascale-plus-overview"
download agilex.html "https://www.intel.com/content/www/us/en/products/details/fpga/agilex.html"
download agilex7.html "https://www.intel.com/content/www/us/en/products/details/fpga/agilex/7-series.html"
download vu13p_ds2.pdf "https://www.xilinx.com/support/documentation/data_sheets/ds890-ultrascale-plus-overview.pdf"
download agilex7_ds.pdf "https://www.intel.com/content/dam/www/public/us/en/documents/datasheets/agilex-7-fpgas-and-soc-fpgas-datasheet.pdf"
echo "DONE"