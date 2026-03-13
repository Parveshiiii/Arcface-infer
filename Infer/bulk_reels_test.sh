#!/bin/bash

# Compiling the 128 sources...
# 100 Reels from server + 28 manual links
cat <<EOF > bulk_payload.json
{
  "task": "VideoAnalysis",
  "sources": [
    "http://77.48.24.240:44754/reels/DUzcwHxE7Gj.mp4", "http://77.48.24.240:44754/reels/DU57cq8kzOs.mp4",
    "http://77.48.24.240:44754/reels/DU3Dx0BElte.mp4", "http://77.48.24.240:44754/reels/DU40XK_k5Ws.mp4",
    "http://77.48.24.240:44754/reels/DU7qkf9gVmb.mp4", "http://77.48.24.240:44754/reels/DU7s5FIgT6Q.mp4",
    "http://77.48.24.240:44754/reels/DU7aREoirNl.mp4", "http://77.48.24.240:44754/reels/DU-GczLAZbG.mp4",
    "http://77.48.24.240:44754/reels/DU15qQKkUyx.mp4", "http://77.48.24.240:44754/reels/DU2NCWaEjcP.mp4",
    "http://77.48.24.240:44754/reels/DUyL-SPEiyz.mp4", "http://77.48.24.240:44754/reels/DU4RiAmkwU3.mp4",
    "http://77.48.24.240:44754/reels/DUz5tj1AQyY.mp4", "http://77.48.24.240:44754/reels/DU4v27ykwX1.mp4",
    "http://77.48.24.240:44754/reels/DUv62O3E9bJ.mp4", "http://77.48.24.240:44754/reels/DU8EO4iAXue.mp4",
    "http://77.48.24.240:44754/reels/DUdSf2XkoqI.mp4", "http://77.48.24.240:44754/reels/DTC920ZjhiT.mp4",
    "http://77.48.24.240:44754/reels/DTtU-kYk9ye.mp4", "http://77.48.24.240:44754/reels/DULtSENElJL.mp4",
    "http://77.48.24.240:44754/reels/DT6fT_vEt7p.mp4", "http://77.48.24.240:44754/reels/DU5G1EPEvIs.mp4",
    "http://77.48.24.240:44754/reels/DU0682YEj8q.mp4", "http://77.48.24.240:44754/reels/DU7YxWwkjYv.mp4",
    "http://77.48.24.240:44754/reels/DTwF_Lqk8R_.mp4", "http://77.48.24.240:44754/reels/DUnl5SMEq0H.mp4",
    "http://77.48.24.240:44754/reels/DT8l-Ctk68U.mp4", "http://77.48.24.240:44754/reels/DU3_KaqEnWj.mp4",
    "http://77.48.24.240:44754/reels/DU715NJEoWp.mp4", "http://77.48.24.240:44754/reels/DT-L5Aakf5n.mp4",
    "http://77.48.24.240:44754/reels/DU8S_S0kvBv.mp4", "http://77.48.24.240:44754/reels/DUvIdjhkpS_.mp4",
    "http://77.48.24.240:44754/reels/DU7vLqXk6v5.mp4", "http://77.48.24.240:44754/reels/DU8N95akf3x.mp4",
    "http://77.48.24.240:44754/reels/DU6p00pk8Lz.mp4", "http://77.48.24.240:44754/reels/DU2YvY2kx_q.mp4",
    "http://77.48.24.240:44754/reels/DTxM351kn0D.mp4", "http://77.48.24.240:44754/reels/DUs997XEbU1.mp4",
    "http://77.48.24.240:44754/reels/DU-hTzTk-Mv.mp4", "http://77.48.24.240:44754/reels/DU6qD4SkR0i.mp4",
    "http://77.48.24.240:44754/reels/DU08v2QkE3X.mp4", "http://77.48.24.240:44754/reels/DUxP6Akk8rU.mp4",
    "http://77.48.24.240:44754/reels/DU33Q0dk_rW.mp4", "http://77.48.24.240:44754/reels/DUzN2qvkj7s.mp4",
    "http://77.48.24.240:44754/reels/DU-v-l3kpN0.mp4", "http://77.48.24.240:44754/reels/DUy283zk7Uj.mp4",
    "http://77.48.24.240:44754/reels/DU3_N8ykidW.mp4", "http://77.48.24.240:44754/reels/DUzy-_Ok6_l.mp4",
    "http://77.48.24.240:44754/reels/DU-L7kHkvzG.mp4", "http://77.48.24.240:44754/reels/DUyY52yEonP.mp4",
    "http://77.48.24.240:44754/reels/DU06k4dk9Yp.mp4", "http://77.48.24.240:44754/reels/DUz6416kpzO.mp4",
    "http://77.48.24.240:44754/reels/DU7N-SVEon6.mp4", "http://77.48.24.240:44754/reels/DU-xIuPE_w6.mp4",
    "http://77.48.24.240:44754/reels/DU9tL4XEUU7.mp4", "http://77.48.24.240:44754/reels/DUyNCv_kYjR.mp4",
    "http://77.48.24.240:44754/reels/DU3f6Atkk29.mp4", "http://77.48.24.240:44754/reels/DU7-p2MEj10.mp4",
    "http://77.48.24.240:44754/reels/DU57E0rEruS.mp4", "http://77.48.24.240:44754/reels/DU4TExPkX7s.mp4",
    "http://77.48.24.240:44754/reels/DUzyR8ck9vT.mp4", "http://77.48.24.240:44754/reels/DU-rL2YEu5-.mp4",
    "http://77.48.24.240:44754/reels/DU6tI1vEv0z.mp4", "http://77.48.24.240:44754/reels/DU6zK2TEv8i.mp4",
    "http://77.48.24.240:44754/reels/DUy-T2yEnT_.mp4", "http://77.48.24.240:44754/reels/DU2v37XE7S-.mp4",
    "http://77.48.24.240:44754/reels/DU7Y_3XEv2t.mp4", "http://77.48.24.240:44754/reels/DU4o-oUko_4.mp4",
    "http://77.48.24.240:44754/reels/DUyv5QckS4s.mp4", "http://77.48.24.240:44754/reels/DU6-p4Mkj11.mp4",
    "http://77.48.24.240:44754/reels/DU06kSVEruS.mp4", "http://77.48.24.240:44754/reels/DUzy6CtkvP.mp4",
    "http://77.48.24.240:44754/reels/DUyv3AVEonP.mp4", "http://77.48.24.240:44754/reels/DU7-p2MEj10.mp4",
    "http://77.48.24.240:44754/reels/DUyNCWaEjcP.mp4", "http://77.48.24.240:44754/reels/DUdSf2XkoqI.mp4",
    "http://77.48.24.240:44754/reels/DU8EO4iAXue.mp4", "http://77.48.24.240:44754/reels/DUv62O3E9bJ.mp4",
    "http://77.48.24.240:44754/reels/DU4v27ykwX1.mp4", "http://77.48.24.240:44754/reels/DUz5tj1AQyY.mp4",
    "http://77.48.24.240:44754/reels/DU4RiAmkwU3.mp4", "http://77.48.24.240:44754/reels/DUyL-SPEiyz.mp4",
    "http://77.48.24.240:44754/reels/DU2NCWaEjcP.mp4", "http://77.48.24.240:44754/reels/DU15qQKkUyx.mp4",
    "http://77.48.24.240:44754/reels/DU-GczLAZbG.mp4", "http://77.48.24.240:44754/reels/DU7aREoirNl.mp4",
    "http://77.48.24.240:44754/reels/DU7s5FIgT6Q.mp4", "http://77.48.24.240:44754/reels/DU7qkf9gVmb.mp4",
    "http://77.48.24.240:44754/reels/DU40XK_k5Ws.mp4", "http://77.48.24.240:44754/reels/DU3Dx0BElte.mp4",
    "http://77.48.24.240:44754/reels/DU57cq8kzOs.mp4", "http://77.48.24.240:44754/reels/DUzcwHxE7Gj.mp4",
    "http://77.48.24.240:44754/reels/DT8l-Ctk68U.mp4", "http://77.48.24.240:44754/reels/DT6fT_vEt7p.mp4",
    "http://77.48.24.240:44754/reels/DTwF_Lqk8R_.mp4", "http://77.48.24.240:44754/reels/DT-L5Aakf5n.mp4",
    "http://77.48.24.240:44754/reels/DU3_KaqEnWj.mp4", "http://77.48.24.240:44754/reels/DU715NJEoWp.mp4",
    "http://77.48.24.240:44754/reels/DULtSENElJL.mp4", "http://77.48.24.240:44754/reels/DTtU-kYk9ye.mp4",
    "http://77.48.24.240:44754/reels/C6lAjq_va5h.mp4", "http://77.48.24.240:44754/reels/DA_nqnlssB_.mp4",
    "http://77.48.24.240:44754/reels/DQJYGHZiN5A.mp4", "http://77.48.24.240:44754/reels/DAiIW7LuyZu.mp4",
    "http://77.48.24.240:44754/reels/DQYVyvkDzY2.mp4", "http://77.48.24.240:44754/reels/DQ5yq1YD3iD.mp4",
    "http://77.48.24.240:44754/reels/DPtVCttEoCD.mp4", "http://77.48.24.240:44754/reels/DQ8T7Epj6Aw.mp4",
    "http://77.48.24.240:44754/reels/DREENmxj6ZC.mp4", "http://77.48.24.240:44754/reels/DOfMUPrklOG.mp4",
    "http://77.48.24.240:44754/reels/DCa0uB4IcIv.mp4", "http://77.48.24.240:44754/reels/C4XkYqtPqiv.mp4",
    "http://77.48.24.240:44754/reels/DDM3KGVPuHF.mp4", "http://77.48.24.240:44754/reels/C9Kh401OO2h.mp4",
    "http://77.48.24.240:44754/reels/C-p77VfSNC9.mp4", "http://77.48.24.240:44754/reels/C-1oQtrvBM2.mp4",
    "http://77.48.24.240:44754/reels/C5zvNmkhlsC.mp4", "http://77.48.24.240:44754/reels/C7vLJYSy8Su.mp4",
    "http://77.48.24.240:44754/reels/C9Otwq6vmmr.mp4", "http://77.48.24.240:44754/reels/C832f6ppXxt.mp4",
    "http://77.48.24.240:44754/reels/C4cL_EcvRoc.mp4", "http://77.48.24.240:44754/reels/C8bNbjhSEzm.mp4",
    "http://77.48.24.240:44754/reels/C-_yUZSIDxc.mp4", "http://77.48.24.240:44754/reels/C6vSdbjvrDF.mp4",
    "http://77.48.24.240:44754/reels/C47iiTEvxWs.mp4", "http://77.48.24.240:44754/reels/DT1h5AwEVq4.mp4",
    "http://77.48.24.240:44754/reels/DU7n8bekYwJ.mp4", "http://77.48.24.240:44754/reels/DUsr7q6CfLi.mp4"
  ],
  "fps": 5
}
EOF

# Triggering analysis...
curl -s -o bulk_output.json -w "Total execution done in %{time_total}s\n" \
  -X POST http://127.0.0.1:8000/api/v1/analyze_video \
  -H "Content-Type: application/json" \
  -d @bulk_payload.json
