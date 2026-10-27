<div align="center">

<img src="https://readme-typing-svg.demolab.com/?lines=NexusSim+%E2%80%94+Real-Time+Multi-Agent+Urban+Traffic+Simulation;48+Algorithms+across+RL%2C+CV%2C+NLP+%26+Soft+Computing;Decentralized+MAPPO+%E2%80%A2+20k+Agents+%E2%80%A2+60+FPS;Equity+%26+Gini+Wait-Time+Analysis&font=Fira%20Code&center=true&width=700&height=50&color=22C55E&vCenter=true&size=24&background=00000000&duration=3000" alt="Typing SVG" />

<p align="center">
  <img src="https://komarev.com/ghpvc/?username=DarkHeaVen1711&label=PROJECT%20VIEWS&color=000000&style=flat&base=100" alt="project views"/>
  <img src="https://img.shields.io/badge/STATUS-ACTIVE-000000?style=flat&labelColor=000000&color=22C55E" alt="status"/>
</p>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<p align="center"><b>A real-time, multi-agent urban traffic simulation and AI research sandbox.</b><br/>
NexusSim models real road topologies from OpenStreetMap, simulates tens of thousands of heterogeneous vehicles with physics-based car-following, executes decentralized AI signal control, measures algorithmic equity, and integrates a unified 48-algorithm portfolio across Reinforcement Learning, Soft Computing, Computer Vision, and Natural Language Processing.</p>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

</div>

<div align="center">

### 🚀 Quickstart

</div>

<table align="center" width="100%">
<tr>
<td align="center" width="33%">

**1-Click (Windows)**
</td>
<td align="center" width="33%">

**Docker (All Platforms)**
</td>
<td align="center" width="33%">

**Manual**
</td>
</tr>
<tr>
<td align="center" style="padding: 10px;">

```bat
run.bat --city piedmont
run.bat --city chicago --agents 2000
run.bat --train --train-city piedmont
```

</td>
<td align="center" style="padding: 10px;">

```bash
docker-compose up --build
```

</td>
<td align="center" style="padding: 10px;">

```bash
cmake -S engine -B engine/build -DCMAKE_BUILD_TYPE=Release
cmake --build engine/build --config Release -j
./engine/build/engine --city piedmont --agents 500 --duration 5
```

</td>
</tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 🏛️ System Architecture

</div>

<table align="center">
<tr>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**C++ Engine**<br>
<sub>Port 9001 • WebSocket</sub><br>
IDM • Quadtree • ONNX • Fuzzy

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**Dashboard**<br>
<sub>Port 3000 • HTTP/WS</sub><br>
React 19 • Vite • Leaflet

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**NLP Chat**<br>
<sub>Port 9004 • REST</sub><br>
FastAPI • Incident Parser

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**Event Bus**<br>
<sub>Port 9005 • WS</sub><br>
Pub/Sub • Cross-Subject

</td>
</tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 🧬 48-Algorithm Portfolio

</div>

<table align="center">
<tr>
<th>📁 Discipline</th>
<th>🔢 Count</th>
<th>🛠️ Stack</th>
<th>📊 Benchmark</th>
</tr>
<tr>
<td align="center">Computer Vision</td>
<td align="center">12</td>
<td align="center">OpenCV • YOLO • DeepSORT</td>
<td align="center">97.5% detection</td>
</tr>
<tr>
<td align="center">Soft Computing</td>
<td align="center">12</td>
<td align="center">GA • PSO • ANFIS • NSGA-II</td>
<td align="center">16.2% MAPE</td>
</tr>
<tr>
<td align="center">NLP</td>
<td align="center">12</td>
<td align="center">FastAPI • Naive Bayes • NER</td>
<td align="center">98.2% accuracy</td>
</tr>
<tr>
<td align="center">Reinforcement Learning</td>
<td align="center">12</td>
<td align="center">MAPPO • PPO • DQN • SAC</td>
<td align="center">+26.3% reward</td>
</tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 📈 Multi-City Benchmarks

</div>

<table align="center" width="100%">
<tr>
<th>🏙️ City</th>
<th>🚦 Intersections</th>
<th>📉 Webster Reward</th>
<th>🚀 MARL Reward</th>
<th>📈 Net Improvement</th>
</tr>
<tr>
<td align="center"><b>Chicago (USA)</b></td>
<td align="center">3,709</td>
<td align="center">-13,973.97</td>
<td align="center">-10,298.50</td>
<td align="center"><b>+26.3%</b></td>
</tr>
<tr>
<td align="center"><b>Toy Grid</b></td>
<td align="center">4</td>
<td align="center">-11,269.82</td>
<td align="center">-5,370.25</td>
<td align="center"><b>+52.3%</b></td>
</tr>
<tr>
<td align="center"><b>Paris (FR)</b></td>
<td align="center">30</td>
<td align="center">-52,783.02</td>
<td align="center">-53,895.10</td>
<td align="center">Baseline Transfer</td>
</tr>
<tr>
<td align="center"><b>Ahmedabad (IN)</b></td>
<td align="center">25</td>
<td align="center">-56,649.00</td>
<td align="center">-58,294.80</td>
<td align="center">Baseline Transfer</td>
</tr>
<tr>
<td align="center"><b>Piedmont (USA)</b></td>
<td align="center">41</td>
<td align="center">-26,606.20</td>
<td align="center">-30,560.61</td>
<td align="center">Baseline Comparison</td>
</tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 🧪 Testing

</div>

<table align="center">
<tr>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**Gateway API**<br>
<sub>38 / 38 passing</sub>

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**Data Pipeline**<br>
<sub>39 / 39 passing</sub>

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**ML & E2E**<br>
<sub>80 / 80 passing</sub>

</td>
<td align="center" style="padding: 10px; border: 1px solid #1a1a1a;" width="25%">

**Dashboard**<br>
<sub>8 / 8 passing</sub>

</td>
</tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 🛠️ Tech Stack

</div>

<table align="center">
<tr><td><b>Engine</b></td><td>

![C++17](https://img.shields.io/badge/-C%2B%2B17-000000?style=flat-square&logo=cplusplus&logoColor=white)
![CMake](https://img.shields.io/badge/-CMake-000000?style=flat-square&logo=cmake&logoColor=white)
![Ninja](https://img.shields.io/badge/-Ninja-000000?style=flat-square&logo=ninja&logoColor=white)
![OpenSSL](https://img.shields.io/badge/-OpenSSL-000000?style=flat-square&logo=openssl&logoColor=white)
![uWebSockets](https://img.shields.io/badge/-uWebSockets-000000?style=flat-square&logo=websocket&logoColor=white)

</td></tr>
<tr><td><b>ML & AI</b></td><td>

![PyTorch](https://img.shields.io/badge/-PyTorch-000000?style=flat-square&logo=pytorch&logoColor=white)
![ONNX](https://img.shields.io/badge/-ONNX-000000?style=flat-square&logo=onnx&logoColor=white)
![NumPy](https://img.shields.io/badge/-NumPy-000000?style=flat-square&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/-Pandas-000000?style=flat-square&logo=pandas&logoColor=white)

</td></tr>
<tr><td><b>Frontend</b></td><td>

![React](https://img.shields.io/badge/-React-000000?style=flat-square&logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/-Vite-000000?style=flat-square&logo=vite&logoColor=white)
![TypeScript](https://img.shields.io/badge/-TypeScript-000000?style=flat-square&logo=typescript&logoColor=white)
![Leaflet](https://img.shields.io/badge/-Leaflet-000000?style=flat-square&logo=leaflet&logoColor=white)

</td></tr>
<tr><td><b>Backend & DevOps</b></td><td>

![FastAPI](https://img.shields.io/badge/-FastAPI-000000?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/-Python-000000?style=flat-square&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/-Docker-000000?style=flat-square&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-000000?style=flat-square&logo=githubactions&logoColor=white)

</td></tr>
</table>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 📊 Project Stats

</div>

<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=DarkHeaVen1711&repo=Nexus_Sim&show_icons=true&theme=transparent&hide_border=true&title_color=ffffff&icon_color=22C55E&text_color=ffffff&bg_color=00000000&ring_color=22C55E" width="48%" alt="NexusSim stats"/>
  <img src="https://github-readme-streak-stats.herokuapp.com/?user=DarkHeaVen1711&theme=transparent&hide_border=true&background=00000000&ring=22C55E&fire=22C55E&currStreakLabel=ffffff&sideLabels=ffffff&dates=888888&currStreakNum=ffffff&sideNums=ffffff" width="48%" alt="GitHub streak"/>
</p>

<p align="center"><img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/></p>

<div align="center">

### 🤝 Connect & Collaborate

<a href="https://github.com/DarkHeaVen1711/Nexus_Sim"><img src="https://img.shields.io/badge/GitHub-Repository-000000?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="https://github.com/DarkHeaVen1711/Nexus_Sim/issues"><img src="https://img.shields.io/badge/Issues-Report-000000?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="https://github.com/DarkHeaVen1711/Nexus_Sim/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-000000?style=for-the-badge&logo=github&logoColor=white" /></a>

</div>

<br>

<p align="center">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=transparent&height=2&color=gradient&customColorList=12&section=divider"/>
</p>

<div align="center">
<i>"Whether navigating the quiet mountain peaks or the heaviest storms, the goal remains the same: quiet the internal noise, care deeply, and walk the path of fire."</i>
</div>
