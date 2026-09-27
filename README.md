<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/header-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/header-light.svg">
    <img alt="AbyssGG — AI that runs on your machine, not in the cloud" src="./assets/header-dark.svg" width="100%">
  </picture>

  <p>
    <a href="https://isvik.org/">Isvik project</a> ·
    <a href="https://github.com/AbyssGG/Isvik">Inference runtime</a> ·
    <a href="https://github.com/AbyssGG?tab=repositories">All repositories</a>
  </p>
</div>

I build native software for local AI on Intel PCs: OpenVINO bindings, inference runtimes, and offline applications in Nim and C++. Model inference stays on-device, with no Python runtime in the deployed path.

## Projects

- **[OpenVINO-Nim-API](https://github.com/AbyssGG/OpenVINO-Nim-API)** — community-maintained Nim bindings for the OpenVINO Runtime C API, with managed and header-faithful raw layers.
- **[Isvik](https://github.com/AbyssGG/Isvik)** — local inference runtime for Intel AI PCs, built in Nim on OpenVINO, with local OpenAI- and Anthropic-compatible API endpoints.
- **[Resonance](https://github.com/AbyssGG/Resonance)** — Nim bindings for the OpenVINO C API and the shared runtime layer behind Isvik and NimVoice.
- **[NimVoice](https://github.com/AbyssGG/NimVoice)** — offline text-to-speech for Windows AI PCs, built with Nim and OpenVINO, with Intel NPU acceleration.
- **[Candlelight](https://github.com/AbyssGG/Candlelight)** — offline Windows security app with file scanning, behavior monitoring, and local LLM explanations for alerts.

## Tech stack

<div align="center">
  <img alt="Nim — core stack" src="https://img.shields.io/badge/Nim-CORE-FFE953?style=for-the-badge&logo=nim&logoColor=111111">
  <img alt="OpenVINO — core stack" src="https://img.shields.io/badge/OpenVINO-CORE-0071C5?style=for-the-badge&logo=intel&logoColor=FFFFFF">
  <img alt="Intel NPU — target hardware" src="https://img.shields.io/badge/Intel_NPU-TARGET_HARDWARE-0D1117?style=for-the-badge&logo=intel&logoColor=0071C5">
  <img alt="C++ — used in Candlelight" src="https://img.shields.io/badge/C%2B%2B-PROJECT%20USE-00599C?style=for-the-badge&logo=cplusplus&logoColor=FFFFFF">
</div>

<p align="center"><sub>Core project stack: Nim + OpenVINO · C++ is used in Candlelight.</sub></p>

<p align="center"><sub>Additional technologies</sub></p>

<p align="center"><sub>Low-level &amp; architecture</sub></p>
<div align="center">
  <img alt="x86" src="https://img.shields.io/static/v1?message=x86&color=4B5563&style=for-the-badge">
  <img alt="ARM" src="https://img.shields.io/static/v1?message=ARM&color=0091BD&style=for-the-badge">
  <img alt="Assembly" src="https://img.shields.io/static/v1?message=Assembly&color=6E7781&style=for-the-badge">
  <img alt="Driver Development" src="https://img.shields.io/static/v1?message=Driver%20Development&color=4B5563&style=for-the-badge">
  <img alt="Win32 API" src="https://img.shields.io/static/v1?message=Win32%20API&color=0078D6&style=for-the-badge&logo=windows&logoColor=FFFFFF">
</div>
<p align="center"><sub>Platforms &amp; deployment</sub></p>
<div align="center">
  <img alt="Linux" src="https://img.shields.io/static/v1?message=Linux&color=FCC624&style=for-the-badge&logo=linux&logoColor=111111">
  <img alt="Windows" src="https://img.shields.io/static/v1?message=Windows&color=0078D6&style=for-the-badge&logo=windows&logoColor=FFFFFF">
  <img alt="Docker" src="https://img.shields.io/static/v1?message=Docker&color=2496ED&style=for-the-badge&logo=docker&logoColor=FFFFFF">
  <img alt="VMware Workstation" src="https://img.shields.io/static/v1?message=VMware%20Workstation&color=607078&style=for-the-badge&logo=vmware&logoColor=FFFFFF">
  <img alt="KVM" src="https://img.shields.io/static/v1?message=KVM&color=D61243&style=for-the-badge">
  <img alt="Windows Hyper-V" src="https://img.shields.io/static/v1?message=Windows%20Hyper-V&color=0078D6&style=for-the-badge&logo=windows&logoColor=FFFFFF">
</div>
<p align="center"><sub>AI, inference &amp; acceleration</sub></p>
<div align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=FFFFFF">
  <img alt="ONNX" src="https://img.shields.io/badge/ONNX-005CED?style=for-the-badge&logo=onnx&logoColor=FFFFFF">
  <img alt="CUDA" src="https://img.shields.io/static/v1?message=CUDA&color=76B900&style=for-the-badge&logo=nvidia&logoColor=FFFFFF">
  <img alt="TensorRT" src="https://img.shields.io/static/v1?message=TensorRT&color=76B900&style=for-the-badge&logo=nvidia&logoColor=FFFFFF">
</div>

<p align="center"><sub>Languages &amp; runtimes</sub></p>
<div align="center">
  <img alt="C" src="https://img.shields.io/static/v1?message=C&color=A8B9CC&style=for-the-badge&logo=c&logoColor=111111">
  <img alt="Java" src="https://img.shields.io/static/v1?message=Java&color=ED8B00&style=for-the-badge&logo=openjdk&logoColor=FFFFFF">
  <img alt="Rust" src="https://img.shields.io/badge/Rust-000000?style=for-the-badge&logo=rust&logoColor=FFFFFF">
  <img alt="Go" src="https://img.shields.io/badge/Go-00ADD8?style=for-the-badge&logo=go&logoColor=FFFFFF">
  <img alt="C sharp" src="https://img.shields.io/badge/C%23-239120?style=for-the-badge&logo=csharp&logoColor=FFFFFF">
  <img alt=".NET" src="https://img.shields.io/badge/.NET-512BD4?style=for-the-badge&logo=dotnet&logoColor=FFFFFF">
</div>

<p align="center"><sub>Web &amp; UI</sub></p>
<div align="center">
  <img alt="JavaScript" src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=111111">
  <img alt="TypeScript" src="https://img.shields.io/static/v1?message=TypeScript&color=3178C6&style=for-the-badge&logo=typescript&logoColor=FFFFFF">
  <img alt="Node.js" src="https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=FFFFFF">
  <img alt="HTML" src="https://img.shields.io/badge/HTML-E34F26?style=for-the-badge&logo=html5&logoColor=FFFFFF">
  <img alt="PHP" src="https://img.shields.io/badge/PHP-777BB4?style=for-the-badge&logo=php&logoColor=FFFFFF">
  <img alt="Qt" src="https://img.shields.io/badge/Qt-41CD52?style=for-the-badge&logo=qt&logoColor=111111">
  <img alt="WebView2" src="https://img.shields.io/badge/WebView2-0D1117?style=for-the-badge">
</div>

<p align="center"><sub>Databases</sub></p>
<div align="center">
  <img alt="SQL" src="https://img.shields.io/static/v1?message=SQL&color=4479A1&style=for-the-badge">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=FFFFFF">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=FFFFFF">
</div>

## Contact

- **Email:** [ww809853@gmail.com](mailto:ww809853@gmail.com)
- **Work email:** [admin@isvik.org](mailto:admin@isvik.org)
- **LinkedIn:** [Profile](https://www.linkedin.com/in/%E4%BC%9F%E6%9D%B0-%E7%8E%8B-b39b5443a/)
- **X:** [@Pension_qe](https://x.com/Pension_qe)
- **YouTube:** [@Pension_qe](https://www.youtube.com/@Pension_qe)
- **Bilibili:** [Profile](https://space.bilibili.com/310843881)

















