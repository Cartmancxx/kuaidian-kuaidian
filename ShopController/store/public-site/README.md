# 静态官网

网站：https://cartmancxx.github.io/kuaidian-kuaidian/
隐私页：https://cartmancxx.github.io/kuaidian-kuaidian/privacy.html

本目录是网站源文件。仓库根 docs 是 GitHub Pages 部署副本；修改后同步复制文件，保留 docs/.nojekyll。无构建工具、数据库、远程脚本、统计或第三方 CDN。

- index.html：GitHub 公测介绍、真实仓库和 v1.0.0 Release 下载链接、初学者安装步骤、未签名及 Mac 未实测披露。
- privacy.html：隐私政策，与扩展内数据说明一致，补充 GitHub 托管访问处理。
- style.css / setup.css / icon128.png：本地样式与图标。
- screenshot-launcher.jpg / screenshot-manager.jpg：现有示例截图，不包含真实店铺账号。

本次 Release 标记 prerelease，链接使用 /releases/tag/v1.0.0 和 /releases/download/v1.0.0/，不用不包含预发布的 /releases/latest。发布前核对实际上传文件名和 SHA256SUMS.txt，发布后点击验证，不能把静态页面已编写当作已部署。

GitHub 公测可公开未签名包，但必须保留真实风险披露。未来商店版另行配置真实商店 ID、匹配助手、签名／公证与实机验收状态；不要把当前公测链接伪装为商店链接，也不要教用户关闭防护。

release-config.json 的 downloadPageUrl 指向官网根、privacyPolicyUrl 指向 privacy.html；修改后需要重新打包扩展。GitHub 是托管方，按其隐私政策处理访问请求。本项目不加入统计或跟踪脚本。
