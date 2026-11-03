# 快店快点 · Chrome 商店上线宣传片

用户选择的 video-shotcraft 自主创作工程。32 秒，1920×1080，30 fps，中文，无配音。实际产品 UI 来自仓库的隔离演示预览，仅用虚构店铺；不访问真实 Chrome 资料。

## 交付

- `out/kuaidian-kuaidian-launch.mp4`：原创音乐 + 音效。
- `out/kuaidian-kuaidian-launch-sfx.mp4`：相同画面与音效，无背景音乐，方便自配音乐。
- `out/kuaidian-kuaidian-poster.png`：1080p 封面。
- `BRIEF.md` / `DESIGN.md`：产品要求、设计、功能到镜头映射、分镜与帧号。
- `THIRD_PARTY_NOTICES.md`：素材来源与许可。
- `out/qa/`：实际渲染帧、参考样片、技术报告；渲染输出不进入 Git。

MP4 与封面通过仓库的 GitHub Release 分发。工程与原创音频可独立复现。

## 重渲

需要 Node.js 22+ 和本机 Chrome（建议使用相同版本以复现字体栅格化）。

```sh
npm ci
npm run render
npm run render:sfx
```

发布前可运行以下步骤（需要 FFmpeg / ffprobe 在 PATH 中；验证还需要 NumPy）：

```sh
python scripts/finalize-pair.py
python scripts/verify-video.py
python scripts/export-qa.py
```

两版先分别通过 `bgm=true/false` 属性渲染同一时间线；最后无损复用主版视频流，保留独立渲染的纯音效音轨，使发布文件的画面逐帧、视频流逐字节一致。这不是从混音中消除音乐。原始纯音效导出保留在 `out/qa/`。

若 Remotion 默认浏览器未安装，它会下载 Chrome Headless Shell；也可在命令后添加 `--browser-executable=<本机 Chrome 路径>`。Windows 默认系统中文字体为 Microsoft YaHei；未分发字体文件，其他系统请选择有使用权的中文字体后更新 `src/Film.tsx` 的 FONT。

## 重采真实 UI

先在仓库根运行：

```sh
python ShopController/scripts/preview_server.py --port 19213
```

另一个终端进入本目录：

```sh
npm run capture
```

采集脚本只连接 `127.0.0.1` 预览，并使用全新无头浏览器会话。可用 `CHROME_PATH` 指定程序位置，用 `PREVIEW_URL` 更改预览地址。产品业务文件不会被修改。产物包括 4x 小窗、2x 整页、元素切片及 `public/textures/layout.json`。`styleframes.html` 是制作前视觉定案，不是运行界面复刻。

## 原创声音

```sh
python -m pip install -r requirements-audio.txt
python scripts/make-audio.py
```

120 BPM / 64 拍 / 48 kHz，固定种子，无第三方采样。镜头帧表与 SFX 钉帧集中在 `src/Film.tsx`。`bgm` 属性只控制音乐，不改画面或 SFX。噪声音效为本项目原创合成，没有使用来源不明确的库内音乐。

## 可复核边界

这是演示宣传片，不是实机操作验收视频。没有模拟已登录的真实商家后台，也没有宣称助手已经签名、公证或 GPT 跨资料兼容已验证。Chrome 商店提供扩展，本地助手仍需独立下载安装。
