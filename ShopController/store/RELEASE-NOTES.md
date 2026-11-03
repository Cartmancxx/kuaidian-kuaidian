# 商店配套助手发布说明 · v1.0.0-store.1

产品名：快店快点。开发者：程大意。公开支持邮箱：cartmancxx@gmail.com。

## 本次更新

- [Chrome 扩展已发布](https://chromewebstore.google.com/detail/快店快点/ckeiapojbffhmmedjajdbnpfongmfjmm)；正式 ID：`ckeiapojbffhmmedjajdbnpfongmfjmm`。
- [新配套 Release](https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0-store.1) 提供绑定商店 ID 的 Windows x64、Mac Apple 芯片与 Intel 助手。
- 产品/协议版本保持 1.0.0，发布标签 `v1.0.0-store.1` 用于区分商店配套渠道；不代表 Chrome 扩展升级为 1.0.1。
- 官网和 README 默认指向商店，商店扩展通过 Chrome 的正常机制更新；助手仍独立安装、独立更新。
- MIT 源码继续公开，旧开发者模式包保留为开发用途。

## 旧版用户迁移

旧 v1.0.0 助手绑定 `hadeebhijljjdebkaiaglaeipajnnind`，不能直接连接商店扩展。先关闭小窗/管理页并备份 `config.json` 和存在的 `.bak`，停用旧已解压扩展，安装商店扩展，再完整解压 v1.0.0-store.1 同架构助手。在解压目录运行 Windows `Install.cmd --replace-identity`（PowerShell：`.\Install.cmd --replace-identity`）或 Mac `./Install.command --replace-identity`。普通重装有身份冲突保护，不会静默换绑。安装保留店铺配置，不迁移 Cookie，不改写 Chrome 资料。完成后重试连接，核对店铺与资料绑定；避免同时启用两份同名扩展。

## 产品能力

- 紧凑店铺小窗、平台分组和搜索；独立管理页。
- 现有 Chrome 资料绑定与配对预览；淘宝/天猫按同一体系检查冲突。
- Windows 小窗申请置顶与状态回读；Mac 普通独立小窗。
- 原生 Chrome 继续管理网页、登录状态与其他插件。
- MV3 最小权限；正式包无演示数据、无远程代码；本地配置和备份。
- 助手自带 .NET 10，附运行时许可通知。

## 状态与边界

扩展上架不代表助手已获操作系统签名、公证或真实环境验收。当前助手未签名／未公证，真实 Windows 安装／置顶、Mac 安装／运行、GPT 跨资料控制仍需验收。Mac 包在 Windows 交叉构建，自动化测试不作为真实安装/Gatekeeper 验证的替代。系统可能阻止运行；不要求用户关闭系统防护。

已知限制：不自动复用旧标签、不自动归组、不迁移 Cookie、不识别店铺真实登录状态。点击成功仅代表打开请求已发出。
