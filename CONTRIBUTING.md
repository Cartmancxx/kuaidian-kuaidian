# 参与快店快点

感谢你的测试、文档改进和代码贡献。当前为 GitHub 开源公测；请先阅读 [README](README.md) 中的运行限制与数据说明。

## 提交问题

在 [Issues](https://github.com/Cartmancxx/kuaidian-kuaidian/issues) 说明：

- Windows／macOS 版本和 CPU 架构、Chrome 版本。
- 扩展与助手版本、从哪个 Release 下载。
- 可重复的操作步骤、预期结果、实际结果。
- 已脱敏的错误文字或截图；不要提交 Cookie、密码、账号令牌、客户信息、订单或真实配置文件。

涉及漏洞请按 [SECURITY](SECURITY.md) 私下联系，不在公开 Issue 放可利用细节或敏感数据。功能建议请描述具体使用场景，特别是是否涉及同平台多账号或跨资料操作。

## 本地开发

1. Fork 仓库并创建一个主题分支。
2. 安装 .NET 10 SDK、Python 3.10+；扩展测试需要 Node.js。核心控制台测试当前还需要 .NET 8 运行时，详见 [测试指南](ShopController.Tests/README.md)。
3. `dotnet build ShopController/host/ShopController.Host.csproj -c Release`。
4. 按测试指南运行受影响的自动化检查；测试使用临时样本，不应读取真实店铺资料或安装助手。
5. 用独立测试 Chrome 资料进行需要真实浏览器的手动测试，明确记录系统、步骤和结果。Mac 代码在 Windows 编译通过不是 Mac 实测证据。

公开 `manifest.key` 仅用于 GitHub 渠道的稳定扩展 ID，不是签名私钥。修改它会改变 ID、需要重新登记助手；提交普通修复时请保持不变。本地 GitHub 公测打包命令为 `python ShopController/scripts/publish_release.py --channel github --dotnet dotnet`。未来商店渠道使用 `--channel store` 并配置实际商店 ID。发布脚本不会自动替你上传商店或 GitHub。

## 提交 Pull Request

- 一个 PR 尽量解决一个问题，说明动机、行为变化与验证范围。
- 界面调整附截图，标注示例数据；不要展示真实商家账号或订单。
- 修改权限、配置格式、安装路径或数据处理时，同步更新文档、隐私说明和测试。
- 保持 shell-free 的 Chrome 参数传递、确切扩展来源绑定和现有资料边界。
- 不引入 Cookie／密码读取、任意命令执行、静默安装、远程脚本或关闭系统防护的流程。
- 不提交 `bin`、`obj`、下载的 SDK、证书、密钥、个人配置或巨大构建包；发布产物通过 Releases 分发。

贡献按仓库 [MIT 许可证](LICENSE) 提供。请确保你有权提交相应内容，并保留第三方版权与许可通知。
