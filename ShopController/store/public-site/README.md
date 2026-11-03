# 静态官网

网站：https://cartmancxx.github.io/kuaidian-kuaidian/
隐私页：https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html

本目录是网站源文件。仓库根 docs 是 GitHub Pages 部署副本；修改后同步公开 HTML、样式、图标与图片，保留 docs/.nojekyll。本 README 是内部维护说明，不必部署。无构建工具、数据库、远程脚本、统计或第三方 CDN。

- index.html：Chrome 商店正式入口、v1.0.0-store.1 三平台配套助手、首次安装与旧版迁移步骤，以及助手未签名/未公证/待实测披露。
- privacy.html：隐私政策，与扩展内数据说明一致，补充 GitHub 托管访问处理。
- style.css / setup.css / icon128.png：本地样式与图标。
- screenshot-launcher.jpg / screenshot-manager.jpg：示例截图，不包含真实店铺账号。

正式商店 ID 为 ckeiapojbffhmmedjajdbnpfongmfjmm；旧开发者模式 ID 为 hadeebhijljjdebkaiaglaeipajnnind。新配套助手链接使用确定的 /releases/tag/v1.0.0-store.1 和 /releases/download/v1.0.0-store.1/；旧包继续保留在 v1.0.0，不静默替换。发布前核对实际上传文件名和 SHA256SUMS.txt，发布后点击验证，不把静态页面已编写当作已部署。

扩展已上架与助手签名/公证/实机验收是不同事项。保留真实状态，不把商店发布当作对助手的安全认证；不要教用户关闭防护。旧版迁移必须备份配置、停用旧扩展，在新包解压目录显式使用 --replace-identity 换绑；普通安装器不会静默覆盖旧身份。

release-config.json 的 downloadPageUrl 指向官网根、privacyPolicyUrl 指向 privacy.html；修改后需要重新打包扩展。GitHub 是托管方，按其隐私政策处理访问请求。本项目不加入统计或跟踪脚本。
