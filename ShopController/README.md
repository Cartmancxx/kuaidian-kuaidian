# 快店快点 1.0

开发者：**程大意** · 公开支持邮箱：**cartmancxx@gmail.com**

一个小窗，按店铺打开指定 Chrome 资料里的后台。保留原生 Chrome 和现有插件，不再从一长串头像资料里找入口。

## 日常界面

- 工具栏图标打开约 320 × 390 的独立小窗；按平台分组、搜索店铺、点击打开。
- Windows 默认申请置顶，可临时取消；Mac 使用普通独立小窗。
- 同一 Chrome 资料中的小窗只保留一份，再点图标会找回它。
- 店铺添加、绑定、配对和设置集中在单独的管理页。
- 原生 Chrome 处理网页、Cookie 和插件；助手按操作启动，不内嵌第二套浏览器。

这是**入口控制器**，不是多 Cookie 标签浏览器。当前不自动整理标签组、不激活旧业务标签、不识别页面实际店铺。打开请求成功不等于已登录。

## 资料复用

3 个不同京东账号与 2 个不同淘宝账号，理论上可分配到 3 份 Chrome 资料。同登录体系的不同账号仍须分开；淘宝和天猫视为同一体系。

配对前明确勾选可用的资料池，主资料可以不选。配对只改绑定，不移动 Cookie，不删除或创建 Chrome 资料。换绑后要在对应资料中正常登录、核对店名。账号昵称由用户维护，未登记的账号不参与冲突检查。

## 当前分发：Chrome 商店 + 独立本地助手

[从 Chrome 商店安装快店快点](https://chromewebstore.google.com/detail/快店快点/ckeiapojbffhmmedjajdbnpfongmfjmm)；正式扩展 ID 为 `ckeiapojbffhmmedjajdbnpfongmfjmm`。商店版本 1.0.0，商店页面显示更新日期 2026-10-29。

[商店配套助手 v1.0.0-store.1](https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0-store.1) 提供绑定正式 ID 的 Windows x64、Mac Apple 芯片与 Intel 包。完整安装与旧版迁移步骤见 [首次安装教程](../README.md)。商店安装不需要开发者模式；本地助手仍须用户另外安装。

**Chrome 商店发布不代表本地助手获得操作系统签名、公证或平台运行验收。** 当前助手未签名、未公证，Mac 未实机安装验收；系统可能阻止运行。请遵循系统与设备策略，不关闭防护。

扩展使用 Chrome 官方 Native Messaging 连接助手。普通扩展单独不负责登记系统程序或跨资料启动。助手只接受绑定的确切扩展 ID。

| 配套文件（来自 v1.0.0-store.1） | 用途 |
| --- | --- |
| `ShopController-helper-1.0.0-win-x64.zip` | Windows 助手，完整解压后运行 Install.cmd |
| `ShopController-helper-1.0.0-osx-arm64.zip` | Apple Silicon Mac 助手，运行 Install.command |
| `ShopController-helper-1.0.0-osx-x64.zip` | Intel Mac 助手，运行 Install.command |
| `ShopController-extension-1.0.0.zip` | 商店投稿构建留档；日常用户请从商店安装 |
| `ShopController-source-1.0.0.zip` | 产品源码、测试、文档和发布脚本 |

目标系统：受支持版本的 Windows 11 x64；macOS 15 及之后受 .NET 10 支持的版本，Apple Silicon / Intel。Chrome 116+，建议最新稳定版。助手自带 .NET 10 运行时，用户无需额外安装 SDK。

### 使用、更新和卸载

1. 安装商店扩展、完整解压并安装 **v1.0.0-store.1** 匹配架构助手后，打开连接页并重试，确认助手版本与已连接状态。
2. 进入管理页，添加店铺、填写平台和账号昵称、后台 HTTP/HTTPS 地址，绑定现有 Chrome 资料。
3. 返回小窗点击店名，在真实网页核对店铺账号；首次登录、扫码和验证仍遵循平台流程。
4. 商店扩展通过 Chrome Web Store 正常更新；本地助手独立更新，不随扩展自动更新。
5. 更新助手：从新下载并解压的配套包运行安装器，旧配置保留。卸载运行 Uninstall.cmd 或 Uninstall.command，移除通信登记并保留配置；Windows 保留程序，Mac 归档程序。扩展单独移除。

Mac 自定义 Chrome 程序路径填写应用内 `Contents/MacOS/Google Chrome`，不是 `.app` 文件夹。Mac 包尚未签名／公证，也没有实机安装成功的验证结论；系统拦截时请反馈脱敏信息，不要关闭 Gatekeeper。

### 旧 GitHub 开发者模式与迁移

旧 [v1.0.0 Release](https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0) 的未打包扩展保留公开 manifest.key，ID 为 `hadeebhijljjdebkaiaglaeipajnnind`。旧助手绑定这个 ID，**不能直接连接正式商店扩展**。

迁移时关闭小窗/管理页并备份 `config.json` 与存在的 `.bak`，停用旧扩展，从商店安装新扩展。完整解压 **v1.0.0-store.1** 助手后，在解压目录显式运行 Windows `Install.cmd --replace-identity`（PowerShell 使用 `.\Install.cmd --replace-identity`）或 Mac `./Install.command --replace-identity`。普通重装有身份冲突保护，不会静默换绑；配置保留，不移动 Cookie 或 Chrome 资料。最后重试连接并核对店铺绑定。一个本地助手登记同一时间绑定一个 ID，避免同时启用两份同名扩展。

开发者仍可用 `--channel github` 生成固定 key 的未打包扩展和同渠道助手。此渠道手动加载、手动刷新，不通过商店自动更新；不要删掉 key 或与商店助手混搭。

公开网站：[安装与下载](https://cartmancxx.github.io/kuaidian-kuaidian/)、[隐私政策](https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html)。

## GPT 与其他扩展

保留原生 Chrome 运行环境，没有内嵌浏览器或远程调试端口。插件安装和授权通常按资料区分，需在每份要使用的资料中分别确认 GPT/Codex 浏览器控制连接。**跨资料 GPT 控制尚未实测，不把保留 Chrome 环境当作兼容性认证。**

## 数据与权限

- 仅 `nativeMessaging`、`storage` 两项扩展权限；无站点读取权限、无内容脚本。
- 助手只从 Chrome Local State 的资料信息中提取目录标识和显示名，不读取 Cookie、密码或历史数据库。
- 保存店铺元数据、后台地址、备注、资料绑定、最近打开时间；这些仍可能是商业信息。
- Windows 配置：`%LOCALAPPDATA%\ShopController\config.json`，上一版备份为 `.bak`。
- Mac 配置：`~/Library/Application Support/ShopController/config.json`，上一版备份为 `.bak`。
- 本产品无云同步、遥测、广告或自己的上传服务。平台、Chrome 和其他插件仍按各自设置联网。
- Windows 置顶只操作 Chrome 传入的调用窗口，验证 Chrome 进程；消息中不接收任意窗口句柄。
- 本地打开通过参数列表启动 Chrome，不拼接 shell 命令。

完整隐私说明见 `extension/privacy.html`。卸载保留配置，完整清除需另行删除本产品配置及备份；不触碰 Chrome 资料。

## 构建和测试

```powershell
# 工作目录：包含 ShopController、ShopController.Core、ShopController.Tests 的目录
python ShopController/scripts/publish_release.py --channel github --output-suffix github --dotnet dotnet
# 商店配套助手：绑定正式扩展 ID
python ShopController/scripts/publish_release.py --channel store --dotnet dotnet --extension-id ckeiapojbffhmmedjajdbnpfongmfjmm --output-suffix store.1
# 仅预览示例数据，不启动真实 Chrome、不连接助手
python ShopController/scripts/preview_server.py --port 19173
```

构建要求 .NET 10 SDK、Python 3.10+，上述命令按渠道输出至 `dist/ShopController-release-1.0.0-store.1` 与 `dist/ShopController-release-1.0.0-github`，不覆盖另一渠道。`--skip-build` 只接受与当前 host/core 源码哈希一致的构建缓存；`--require-publish-ready` 是更严格的成熟分发质量预检，不是源码公开或扩展已上架的证明；不会凭配置布尔值声称已签名或已实测。

测试命令见 `ShopController.Tests/README.md`。预览仅经开发服务器替换 API；正式扩展硬编码 `isDemo=false`，不包含示例账号模块。

`ShopController/scripts/publish.ps1` 与同目录旧“安装本地助手”脚本为早期 Windows 开发流程，**1.0 分发统一使用 publish_release.py 和 scripts/release 中的新安装器**。

## 发布素材与许可

`store` 包含中文文案、英文审核说明、权限说明、真实页面示例截图、公开网站文件及检查清单。产品源码与文档按 [MIT License](LICENSE) 开源，Copyright © 2026 程大意。运行时许可证和第三方通知随助手包附带，各自遵循原许可。网站源在 store/public-site，GitHub Pages 部署副本位于仓库根 docs。

官方参考：[Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)、[商店发布流程](https://developer.chrome.com/docs/webstore/publish)、[素材要求](https://developer.chrome.com/docs/webstore/images)、[.NET 10 系统矩阵](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)。

