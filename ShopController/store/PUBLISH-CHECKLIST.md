# 快店快点 · 商店配套与开源发布清单

本仓库按 MIT 开源。**GitHub 公开源码／公测与 Chrome Web Store 审核是不同渠道**；不能因为未签名就声称源码不可公开，也不能因为 GitHub 包可下载就声称已通过商店审核或平台验收。

## A. 当前商店配套渠道

- 商店：https://chromewebstore.google.com/detail/快店快点/ckeiapojbffhmmedjajdbnpfongmfjmm
- 正式扩展 ID：`ckeiapojbffhmmedjajdbnpfongmfjmm`。
- 配套助手：https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0-store.1
- 官网：https://cartmancxx.github.io/kuaidian-kuaidian/
- 隐私：https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html

1. 用 `python ShopController/scripts/publish_release.py --channel store --extension-id ckeiapojbffhmmedjajdbnpfongmfjmm --output-suffix store.1 --dotnet dotnet` 构建。助手身份文件与 native host `allowed_origins` 必须精确绑定正式 ID。
2. 本次产品版本仍 1.0.0；用独立标签 `v1.0.0-store.1` 发布商店配套助手，保留旧 `v1.0.0` 资产。禁止在同一路径静默覆盖不同身份的包。
3. 核对产物没有密码、个人资料、真实店铺配置、证书或私钥；保留 MIT 与运行时许可通知。
4. 运行自动化测试与 ZIP 校验，生成当前文件的 SHA256SUMS.txt。任何重新构建或签名后必须重新计算摘要。
5. README、Release 和官网标明：扩展已发布，但助手未签名／未公证、Mac 未实机安装验收、真实 Chrome／Windows 置顶／GPT 跨资料控制待实测。不要把商店发布当作助手安全认证。
6. 提供旧 GitHub ID 迁移步骤：备份配置、停用旧扩展、安装商店扩展、在解压目录显式运行 Windows `Install.cmd --replace-identity` 或 Mac `./Install.command --replace-identity`、重试连接与核对绑定。保持用户配置与 Chrome 资料不变。
7. GitHub Pages 从仓库根 docs 部署；与 store/public-site 镜像一致。检查商店链接、三平台下载、隐私页、图片和摘要实际可访问，再告知用户更新完成。

未签名包可能遇到系统拦截。不得提供关闭 Gatekeeper、防病毒或设备安全策略的指引。摘要用于核对内容，不等同于代码签名或安全认证。

## B. 后续商店扩展更新

1. 保持正式商店项目与 ID；商店 ZIP 不带开发用 key，仅上传扩展，不上传助手或源码包。
2. 有功能修改时按 Chrome 商店规则递增扩展版本，更新文案与隐私声明并提交审核；当前仅配套分发更新不虚构新扩展版本。
3. 助手或协议有变动时，同时提供兼容版本、迁移说明与绑定正式 ID 的助手下载。扩展自动更新不等于助手自动更新。
4. 为准备承诺支持的平台完成真实安装、更新、卸载与 Chrome 路由验证。Windows 签名、Mac Developer ID 签名和公证作为后续分发改进，证书不进入源码库。
5. 签名改变文件后重打包、重算摘要；如新增验收结论，附真实证据，不只改配置布尔值。
6. 用 LISTING.zh-CN.md、PRIVACY-FIELDS.md、REVIEWER-INSTRUCTIONS.en.md 维护审核资料；每次更新审核结果独立，以商店状态为准。

## C. 保留 GitHub 开发者模式

旧渠道： https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0 ，公开 key 对应 ID `hadeebhijljjdebkaiaglaeipajnnind`。

用 `--channel github --output-suffix github` 构建含 key 的未打包扩展和绑定其派生 ID 的助手。用户手动加载/刷新，配套助手不得混用商店版。不要删除旧资产，也不要用 `/releases/latest` 替换历史下载地址。一个本地助手登记同一时间绑定一个 ID。

## 真实环境验收表（完成后附证据）

- [ ] Windows 11 x64 全新测试用户：Install.cmd 无管理员安装，连接页显示版本。
- [ ] 两份测试 Chrome 资料分别打开公开示例页；真实商家页另外核对实际店名。
- [ ] 多管理页同时保存：过期修订拒绝，刷新可继续。
- [ ] Windows 小窗：首次置顶、取消、切焦点不重置；普通页面不操作置顶。
- [ ] Mac Apple 芯片：下载、系统安全检查、安装、连接、路由、更新、卸载。
- [ ] Mac Intel：同上；无置顶控件和 Win32 调用。
- [ ] 旧配置保留、旧程序备份、身份变更需显式确认；其他助手登记不受影响。
- [ ] 卸载仅撤销本产品通信登记，保留配置和 Chrome 登录数据；程序保留／归档行为符合文档。
- [ ] GPT／Codex 在每份资料分别连接，完成无敏感数据页面控制测试；仅能打开网页不是兼容证明。
- [ ] 公开页面和真实下载链接可访问、摘要匹配、无凭据、无真实账号截图。

## 构建门槛与证据

`release-manifest.json` 记录真实未完成项。`--require-publish-ready` 仅检查对应渠道的必需元数据（包括商店渠道的扩展 ID）；通过此检查不代表助手已签名、公证或完成实机安装验收。签名和实测限制仍保留在 `warnings`，不得删除风险披露、假造已完成状态或把布尔开关当作验证证据。

## 官方参考

- [Chrome 加载未打包扩展](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked)
- [Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Chrome 商店发布](https://developer.chrome.com/docs/webstore/publish)
- [固定扩展 ID / key](https://developer.chrome.com/docs/extensions/reference/manifest/key)
- [.NET 10 支持系统](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)
- [Apple 公证](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
