# HPCC Validation Result Analysis

Generated from existing HPCC output artifacts.

## Run Summary

| Run | Input OK | Input Flows | Flows | Drained | Mean FCT | P90 FCT | Max FCT | Mean Slowdown | PFC | Bottleneck | Max Q | Q/Kmax | Qlen Max | Trace Records | Warnings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dcqcn_fb_30 | yes | 995249 | 995249 | yes | 0.041 | 0.057 | 8.913 | 1.6x | 0 | n/a | n/a | n/a | 3057 KB | n/a | 1 |
| hpcc_fb_30 | yes | 995249 | 996506 | yes | 7.405 | 0.067 | 155.539 | 480.1x | 0 | n/a | n/a | n/a | 547 KB | 0 | 2 |
| hpcc_ws_30 | yes | 69635 | 29099 | no | 0.313 | 0.907 | 14.030 | 1.6x | 0 | n/a | n/a | n/a | 0 KB | n/a | 3 |
| hpcc_ws_50-1 | yes | 117068 | 107480 | no | 66.286 | 238.890 | 659.445 | 984.8x | 18370177 | n/a | n/a | n/a | 24344 KB | n/a | 4 |

## FCT By Flow Size Bucket

| Run | Size | Flows | Min FCT | Median FCT | P90 FCT | P99 FCT | Max FCT | Median Slowdown | P99 Slowdown | Max Slowdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dcqcn_fb_30 | <1KB | 598866 | 0.004 | 0.012 | 0.034 | 0.082 | 0.264 | 1.0x | 8.1x | 59.2x |
| dcqcn_fb_30 | 1-10KB | 100370 | 0.004 | 0.013 | 0.034 | 0.082 | 0.257 | 1.0x | 8.0x | 46.4x |
| dcqcn_fb_30 | 10-100KB | 183584 | 0.005 | 0.019 | 0.045 | 0.092 | 0.262 | 1.2x | 6.4x | 27.7x |
| dcqcn_fb_30 | 100KB-1MB | 88130 | 0.013 | 0.050 | 0.130 | 0.472 | 1.108 | 1.5x | 6.2x | 16.9x |
| dcqcn_fb_30 | 1-10MB | 24299 | 0.095 | 0.507 | 1.715 | 3.229 | 8.913 | 2.1x | 6.5x | 11.6x |
| hpcc_fb_30 | <1KB | 570633 | 0.004 | 0.012 | 0.014 | 0.023 | 0.053 | 1.0x | 2.0x | 8.2x |
| hpcc_fb_30 | 1-10KB | 96307 | 0.004 | 0.013 | 0.015 | 0.023 | 0.046 | 1.0x | 2.1x | 6.0x |
| hpcc_fb_30 | 10-100KB | 222035 | 0.005 | 0.021 | 154.451 | 155.431 | 155.539 | 1.3x | 10101.4x | 10108.5x |
| hpcc_fb_30 | 100KB-1MB | 83989 | 0.013 | 0.049 | 0.150 | 0.308 | 1.221 | 1.6x | 4.3x | 12.8x |
| hpcc_fb_30 | 1-10MB | 23542 | 0.105 | 0.422 | 1.678 | 3.210 | 6.883 | 2.1x | 6.5x | 18.0x |
| hpcc_ws_30 | <1KB | 446 | 0.004 | 0.012 | 0.012 | 0.017 | 0.019 | 1.0x | 1.5x | 2.4x |
| hpcc_ws_30 | 1-10KB | 3943 | 0.004 | 0.013 | 0.014 | 0.019 | 0.032 | 1.0x | 1.6x | 3.1x |
| hpcc_ws_30 | 10-100KB | 11493 | 0.005 | 0.017 | 0.026 | 0.038 | 0.074 | 1.2x | 2.3x | 3.9x |
| hpcc_ws_30 | 100KB-1MB | 4650 | 0.015 | 0.066 | 0.177 | 0.323 | 1.057 | 1.6x | 4.4x | 12.9x |
| hpcc_ws_30 | 1-10MB | 7826 | 0.103 | 0.508 | 1.512 | 2.945 | 5.895 | 2.0x | 5.8x | 16.0x |
| hpcc_ws_30 | >=10MB | 741 | 1.122 | 3.541 | 5.934 | 8.239 | 14.030 | 2.1x | 4.8x | 6.1x |
| hpcc_ws_50-1 | <1KB | 1776 | 0.004 | 0.046 | 1.490 | 3.103 | 5.266 | 4.0x | 273.6x | 616.5x |
| hpcc_ws_50-1 | 1-10KB | 15898 | 0.009 | 0.291 | 7.661 | 18.046 | 41.503 | 25.5x | 1433.5x | 3202.4x |
| hpcc_ws_50-1 | 10-100KB | 46171 | 0.052 | 1.974 | 54.538 | 135.175 | 310.562 | 125.6x | 7824.0x | 16820.7x |
| hpcc_ws_50-1 | 100KB-1MB | 17855 | 0.563 | 19.183 | 273.780 | 498.349 | 647.121 | 324.9x | 11668.0x | 20817.5x |
| hpcc_ws_50-1 | 1-10MB | 24863 | 5.820 | 131.583 | 392.568 | 578.847 | 655.760 | 395.0x | 3257.6x | 6147.1x |
| hpcc_ws_50-1 | >=10MB | 917 | 78.835 | 428.809 | 569.086 | 636.611 | 659.445 | 292.9x | 616.0x | 701.4x |

## PFC And Bottleneck

| Run | Events | Pause | Resume | Balanced | Queues | First ms | Last ms | Max Row | Max Egress | Q/Kmax | ECN | Pause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dcqcn_fb_30 | 0 | 0 | 0 | yes | 0 | n/a | n/a | n/a | n/a | n/a | no | no |
| hpcc_fb_30 | 0 | 0 | 0 | yes | 0 | n/a | n/a | n/a | n/a | n/a | no | no |
| hpcc_ws_30 | 0 | 0 | 0 | yes | 0 | n/a | n/a | n/a | n/a | n/a | no | no |
| hpcc_ws_50-1 | 18370177 | 9185156 | 9185021 | no | 521 | 2000.762 | 2663.390 | n/a | n/a | n/a | no | no |

## Queue Distribution

| Run | Dumps | Final Time ns | Ports | Max Port | Mean | P95 | P99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dcqcn_fb_30 | 6 | 2500000000 | 640 | sw327 port14 | 15.25 KB | 4 KB | 508 KB | 3057 KB |
| hpcc_fb_30 | 11 | 3000000000 | 640 | sw338 port9 | 85.06 KB | 546 KB | 547 KB | 547 KB |
| hpcc_ws_30 | 1 | 2000000000 | 640 | sw320 port1 | 0.00 KB | 0 KB | 0 KB | 0 KB |
| hpcc_ws_50-1 | 7 | 2600000000 | 640 | sw354 port1 | 285.53 KB | 17 KB | 19493 KB | 24344 KB |

## Trace Files

| Run | Bytes | Ports | Records | Data | ACK/NACK | PFC | Host Records | Switch Records |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dcqcn_fb_30 | 8192 | 960 | n/a | n/a | n/a | n/a | n/a | n/a |
| hpcc_fb_30 | 10568 | 960 | 0 | n/a | n/a | n/a | n/a | n/a |
| hpcc_ws_30 | 8192 | 960 | n/a | n/a | n/a | n/a | n/a | n/a |
| hpcc_ws_50-1 | 8192 | 960 | n/a | n/a | n/a | n/a | n/a | n/a |

## Warnings

- dcqcn_fb_30: trace.tr is smaller than its SimSetting header
- hpcc_fb_30: fct.txt has 996506 row(s), expected 995249 from flow_file
- hpcc_fb_30: missing bottleneck.txt
- hpcc_ws_30: fct.txt has 29099 row(s), expected 69635 from flow_file
- hpcc_ws_30: missing bottleneck.txt
- hpcc_ws_30: trace.tr is smaller than its SimSetting header
- hpcc_ws_50-1: pfc.txt:18370178 has 1 columns, expected 6
- hpcc_ws_50-1: fct.txt has 107480 row(s), expected 117068 from flow_file
- hpcc_ws_50-1: missing bottleneck.txt
- hpcc_ws_50-1: trace.tr is smaller than its SimSetting header
