<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/header-light.svg">
  <img alt="AbyssGG — native local AI inference runtimes" src="./assets/header-dark.svg" width="100%">
</picture>

<br><br>

<a href="https://github.com/AbyssGG?tab=repositories"><img alt="Nim" src="https://img.shields.io/badge/Nim-0D1117?style=flat-square&logo=nim&logoColor=FFE953"></a>
<img alt="C++" src="https://img.shields.io/badge/C%2B%2B-0D1117?style=flat-square&logo=cplusplus&logoColor=00599C">
<img alt="OpenVINO" src="https://img.shields.io/badge/OpenVINO-0D1117?style=flat-square&logo=intel&logoColor=0071C5">
<img alt="Intel NPU" src="https://img.shields.io/badge/Intel_NPU-0D1117?style=flat-square&logo=intel&logoColor=0071C5">
<img alt="ONNX" src="https://img.shields.io/badge/ONNX-0D1117?style=flat-square&logo=onnx&logoColor=D0D6E0">
<img alt="CMake" src="https://img.shields.io/badge/CMake-0D1117?style=flat-square&logo=cmake&logoColor=DA3434">

</div>

<br>

I build **fully offline AI inference stacks in Nim** — runtime, bindings, and the models on top —
targeting Intel AI PCs and the NPU. No Python in the hot path, no cloud round-trip.

<br>

### Currently

- **[Isvik](https://github.com/AbyssGG/Isvik)** — a native local inference runtime platform for Intel AI PCs. 100% Nim + OpenVINO.
- **[Resonance](https://github.com/AbyssGG/Resonance)** — the OpenVINO C API binding layer underneath it, with NPU-oriented runtime helpers.
- **[NimVoice](https://github.com/AbyssGG/NimVoice)** — offline TTS built on Resonance, NPU-accelerated end to end.

<br>

### Selected work

| Project | What it is | Stack | License |
| :-- | :-- | :-- | :-- |
| [**Isvik**](https://github.com/AbyssGG/Isvik) | High-performance native local AI inference runtime for Intel AI PCs | Nim · OpenVINO | Apache-2.0 |
| [**Resonance**](https://github.com/AbyssGG/Resonance) | Nim wrapper over the OpenVINO C API + NPU runtime helpers | Nim | Apache-2.0 |
| [**NimVoice**](https://github.com/AbyssGG/NimVoice) | Fully offline local TTS, Intel NPU accelerated | Nim · OpenVINO | MIT |
| [**Candlelight**](https://github.com/AbyssGG/Candlelight) | *(add a one-line description)* | C++ | GPL-3.0 |

<br>

<!--
  可选：GitHub 统计卡片。
  公共实例 github-readme-stats.vercel.app 长期被限流（会显示 "Error / 503"），
  想用就自己 fork + 部署到 Vercel，把下面的域名换成你自己的实例，再取消注释。
-->
<!--
<div align="center">
  <img height="150" alt="stats" src="https://<your-instance>.vercel.app/api?username=AbyssGG&show_icons=true&hide_border=true&bg_color=00000000&title_color=22D3EE&icon_color=6366F1&text_color=8B949E&include_all_commits=true">
  <img height="150" alt="languages" src="https://<your-instance>.vercel.app/api/top-langs/?username=AbyssGG&layout=compact&hide_border=true&bg_color=00000000&title_color=22D3EE&text_color=8B949E&langs_count=6">
</div>
-->

<div align="center">
<sub>Reach me through issues on any of the repos above.</sub>
</div>
