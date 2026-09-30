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

I build native software for local AI on Intel PCs, from OpenVINO bindings and inference runtimes to offline applications in Nim and C++. I also work with AMD GPU compute using ROCm and HIP, and maintain an experimental NVIDIA TensorRT path in Isvik.cpp. Model inference stays on-device, with no Python runtime in the deployed path.

## Projects

- **[Isvik](https://github.com/AbyssGG/Isvik)** — native local inference runtime for Intel AI PCs, built in Nim and OpenVINO, with OpenAI- and Anthropic-compatible local API endpoints.
- **[Isvik.cpp](https://github.com/AbyssGG/Isvik.cpp)** — C++20 local AI runtime with OpenVINO as its primary backend and experimental NVIDIA TensorRT support.
- **[OpenVINO-Nim-API](https://github.com/AbyssGG/OpenVINO-Nim-API)** — community-maintained Nim bindings for the OpenVINO Runtime C API, with managed and header-faithful raw layers.
- **[Resonance](https://github.com/AbyssGG/Resonance)** — reusable Nim wrappers for OpenVINO inference, shared by Isvik and NimVoice.
- **[NimVoice](https://github.com/AbyssGG/NimVoice)** — offline Windows text-to-speech built with Nim and OpenVINO, with Intel NPU acceleration.
- **[Candlelight](https://github.com/AbyssGG/Candlelight)** — offline Windows security app with file scanning, behavior monitoring, and local AI explanations for alerts.
- **[Cairn-Skill](https://github.com/AbyssGG/Cairn-Skill)** — an agent skill that turns repository history into source-backed development logs.

## Core stack

<p align="center"><sub>NVIDIA acceleration</sub></p>
<div align="center">
  <a href="https://github.com/AbyssGG/Isvik.cpp"><img alt="CUDA — NVIDIA GPU compute" src="https://img.shields.io/badge/CUDA-GPU_COMPUTE-76B900?style=for-the-badge&logo=nvidia&logoColor=FFFFFF"></a>
  <a href="https://github.com/AbyssGG/Isvik.cpp"><img alt="TensorRT — experimental Isvik.cpp backend" src="https://img.shields.io/badge/TensorRT-EXPERIMENTAL-76B900?style=for-the-badge&logo=nvidia&logoColor=FFFFFF"></a>
</div>

<p align="center"><sub>Intel platform</sub></p>
<div align="center">
  <a href="https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html"><img alt="Intel oneAPI — software platform" src="https://img.shields.io/badge/oneAPI-INTEL_PLATFORM-0071C5?style=for-the-badge&logo=intel&logoColor=FFFFFF"></a>
  <img alt="OpenVINO — core inference runtime" src="https://img.shields.io/badge/OpenVINO-CORE-0071C5?style=for-the-badge&logo=intel&logoColor=FFFFFF">
  <img alt="Intel NPU — target hardware" src="https://img.shields.io/badge/Intel_NPU-TARGET_HARDWARE-0D1117?style=for-the-badge&logo=intel&logoColor=0071C5">
</div>

<p align="center"><sub>Core languages</sub></p>
<div align="center">
  <img alt="Nim — core language" src="https://img.shields.io/badge/Nim-CORE-FFE953?style=for-the-badge&logo=nim&logoColor=111111">
  <img alt="C++ — used in Isvik.cpp and Candlelight" src="https://img.shields.io/badge/C%2B%2B-PROJECT%20USE-00599C?style=for-the-badge&logo=cplusplus&logoColor=FFFFFF">
</div>

<p align="center"><sub>Isvik is primarily built with Nim + OpenVINO; Isvik.cpp adds an experimental TensorRT path. C++ is also used in Candlelight.</sub></p>

<details open>
<summary>Other tools and technologies</summary>

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
  <a href="https://rocm.docs.amd.com/"><img alt="AMD ROCm — GPU compute" src="https://img.shields.io/badge/AMD_ROCm-GPU_COMPUTE-ED1C24?style=for-the-badge&logo=amd&logoColor=FFFFFF"></a>
  <a href="https://rocm.docs.amd.com/projects/HIP/"><img alt="HIP — AMD GPU programming" src="https://img.shields.io/badge/HIP-AMD_GPU-ED1C24?style=for-the-badge&logo=amd&logoColor=FFFFFF"></a>
  <a href="https://rocm.docs.amd.com/projects/AMDMIGraphX/en/latest/"><img alt="MIGraphX — AMD inference" src="https://img.shields.io/badge/MIGraphX-AMD%20INFERENCE-ED1C24?style=for-the-badge&logo=amd&logoColor=FFFFFF"></a>
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
  <a href="https://slint.dev/"><img alt="Slint — GUI toolkit" src="https://img.shields.io/badge/Slint-GUI%20TOOLKIT-2379F4?style=for-the-badge"></a>
</div>

<p align="center"><sub>Databases</sub></p>
<div align="center">
  <img alt="SQL" src="https://img.shields.io/static/v1?message=SQL&color=4479A1&style=for-the-badge">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=FFFFFF">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=FFFFFF">
</div>

</details>

## Contact

<div align="center">
  <a href="mailto:ww809853@gmail.com"><img alt="Email: ww809853@gmail.com" src="https://img.shields.io/badge/Email-ww809853%40gmail.com-D14836?style=for-the-badge&logo=gmail&logoColor=FFFFFF"></a>
  <a href="mailto:admin@isvik.org"><img alt="Work email: admin@isvik.org" src="https://img.shields.io/badge/Work%20Email-admin%40isvik.org-35495E?style=for-the-badge"></a>
  <a href="https://www.linkedin.com/in/%E4%BC%9F%E6%9D%B0-%E7%8E%8B-b39b5443a/"><img alt="LinkedIn" src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=for-the-badge&logo=linkedin&logoColor=FFFFFF"></a>
  <a href="https://x.com/Pension_qe"><img alt="X" src="https://img.shields.io/badge/X-%40Pension_qe-000000?style=for-the-badge&logo=x&logoColor=FFFFFF"></a>
  <a href="https://www.youtube.com/@Pension_qe"><img alt="YouTube" src="https://img.shields.io/badge/YouTube-Channel-FF0000?style=for-the-badge&logo=youtube&logoColor=FFFFFF"></a>
  <a href="https://space.bilibili.com/310843881"><img alt="Bilibili" src="https://img.shields.io/badge/Bilibili-Profile-00A1D6?style=for-the-badge&logo=bilibili&logoColor=FFFFFF"></a>
</div>
