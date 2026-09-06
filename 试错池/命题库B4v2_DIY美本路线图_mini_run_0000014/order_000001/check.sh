#!/bin/bash
set +e
wc -c 路线图_普高起点.md | awk '{exit !($1>=1500)}' && echo "1_OK" || echo "1_FAIL"
wc -c 路线图_国际部起点.md | awk '{exit !($1>=1500)}' && echo "2_OK" || echo "2_FAIL"
wc -c 路线图_美高起点.md | awk '{exit !($1>=1500)}' && echo "3_OK" || echo "3_FAIL"
grep -q "截至训练数据，需核" 标化时间线.md && echo "4_OK" || echo "4_FAIL"
grep -q "需核" 选校分层法.md && grep -q "Common Data Set" 选校分层法.md && echo "5_OK" || echo "5_FAIL"
grep -q "需核" 中介费对照.md && grep -qE '美元|USD|\$' 中介费对照.md && echo "6_OK" || echo "6_FAIL"
wc -l 需核清单.md | awk '{exit !($1>=15)}' && echo "7_OK" || echo "7_FAIL"
timeout 60 bash -c "$(head -1 运行命令.txt)" >/dev/null && echo "8_OK" || echo "8_FAIL"