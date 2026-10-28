# 快店快点 · GitHub 公测与未来商店发布清单

本仓库按 MIT 开源。**GitHub 公开源码／公测与 Chrome Web Store 审核是不同渠道**；不能因为未签名就声称源码不可公开，也不能因为 GitHub 包可下载就声称已通过商店审核或平台验收。

## A. 当前 GitHub 公开测试版

- 仓库：https://github.com/Cartmancxx/kuaidian-kuaidian
- 本次预发布：https://github.com/Cartmancxx/kuaidian-kuaidian/releases/tag/v1.0.0
- 官网：https://cartmancxx.github.io/kuaidian-kuaidian/
- 隐私：https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html
- 固定公开 key 对应扩展 ID：`hadeebhijljjdebkaiaglaeipajnnind`。

1. 用 `python ShopController/scripts/publish_release.py --channel github --dotnet dotnet` 构建。GitHub 扩展包名含 `extension-unpacked`，保留 manifest.key；本地助手精确绑定同一 ID。
2. 核对产物没有密码、个人资料、真实店铺配置、证书或私钥；保留 MIT 与运行时许可通知。
3. 运行自动化测试与 ZIP 校验，生成当前文件的 SHA256SUMS.txt。任何重新构建或签名后必须重新计算摘要。
4. 将 `v1.0.0` 标记为 **Pre-release / 公开测试版**，上传扩展、三架构助手、源码与摘要。GitHub 的 `/releases/latest` 不用于本次预发布链接；使用确定的 tag 和下载路径。
5. 在 README、Release 和官网醒目标注：未签名／未公证、Mac 未实机运行验收、真实 Chrome／Windows 置顶／GPT 跨资料控制尚待实测。用户先解压加载扩展，再安装助手。
6. GitHub Pages 从仓库根 `docs` 部署；内容来自 `store/public-site`。检查公开下载链接、隐私页和图片实际可访问，再告知用户发布完成。

未签名包可能遇到系统拦截。不得提供关闭 Gatekeeper、防病毒或设备安全策略的指引。摘要用于核对内容，不等同于代码签名或安全认证。

## B. 未来 Chrome Web Store 渠道

以下是后续商店投稿准备，不是开源仓库公开的前提。签名和实机验收是本项目更成熟分发的质量要求，不应冒充 GitHub 或 Chrome Web Store 对所有开源项目的统一规定。

1. 以 `--channel store` 生成不带 key 的商店 ZIP，上传新项目草稿；只传扩展，不传助手或源码包。
2. 取得该项目真实扩展 ID。为商店渠道生成绑定该 ID 的助手，不能默认沿用 GitHub ID。记录两个渠道的迁移与安装方式。
3. 配置真实 HTTPS 下载页和隐私页，并提供审核人员能下载使用的匹配助手；不使用占位链接。
4. 为准备承诺支持的平台完成真实安装、更新、卸载与 Chrome 路由验证。准备 Windows 发布者签名；Mac 使用自己的 Developer ID 和 Apple 公证凭据完成签名／公证，并在浏览器下载场景验证 Gatekeeper 行为。证书不进入源码库。
5. 签名改变文件后重新打包、重算 SHA256，按真实状态更新说明；Windows 交叉构建不能替代 Mac 实机验证。
6. 更新 REVIEWER-INSTRUCTIONS.en.md，明确本次商店 ID 和匹配助手；GitHub 公测包不能被误写成商店审核构建。
7. 用 LISTING.zh-CN.md、PRIVACY-FIELDS.md、图标和示例截图填写商品页面与隐私实践，再提交审核。价格、地区及发布者身份由发布者自行确认。
8. 审核结果由 Chrome Web Store 决定。获批前不显示商店安装按钮或“已通过审核”字样。

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

`release-manifest.json` 记录真实未完成项。`--require-publish-ready` 是严格的后续商店／签名发布预检；GitHub 未签名公测不需要假造已签名状态来通过它。保留风险披露和待办，使用对应渠道的检查，不删除真实待办或把布尔开关当作签名、公证、实测证据。

## 官方参考

- [Chrome 加载未打包扩展](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world#load-unpacked)
- [Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Chrome 商店发布](https://developer.chrome.com/docs/webstore/publish)
- [固定扩展 ID / key](https://developer.chrome.com/docs/extensions/reference/manifest/key)
- [.NET 10 支持系统](https://github.com/dotnet/core/blob/main/release-notes/10.0/supported-os.md)
- [Apple 公证](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
