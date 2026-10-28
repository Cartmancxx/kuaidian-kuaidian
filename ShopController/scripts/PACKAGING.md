# 发布打包

打包脚本仅生成文件，不运行安装器、不登记本地助手、不启动浏览器，也不向远端上传。

## GitHub 公开测试渠道

```powershell
python ShopController/scripts/publish_release.py --channel github --dotnet <dotnet路径>
# 已有相同 SDK、RID 与 host/Core 源码指纹的二进制缓存时：
python ShopController/scripts/publish_release.py --channel github --skip-build --dotnet <dotnet路径>
```

PowerShell 包装器提供对应 `-Channel github -SkipBuild -Dotnet <路径>` 参数。

- 生产加载包：`ShopController-extension-unpacked-<version>.zip`，manifest 位于根目录，保留公开 `manifest.key`，不含演示模块。
- 固定 ID 来自 key 的 DER 字节 SHA-256 前 128 位，以 a–p 编码。当前为 `hadeebhijljjdebkaiaglaeipajnnind`。这是开发者模式加载身份，不代表商店审核或代码签名。
- 三个助手包自动绑定此 ID，安装器将同一 ID 写入宿主身份文件和 Chrome 白名单。不要改 key，或把不同渠道的助手与扩展混搭。
- 无 key 的商店上传包仍同时生成。没有正式商店 ID 不影响 GitHub 渠道，商店 ID 也不会覆盖 GitHub key 派生的身份。
- Windows 未签名、Mac 未公证、Mac 真实机器验收尚未完成等信息写入 `warnings`，保留公开测试版的真实限制，不阻止生成 GitHub 包。
- `--require-publish-ready` 在 GitHub 渠道检查发布者/支持邮箱/HTTPS 网址元数据，不将未签名或没有商店 ID 当作 GitHub 打包错误；它不代表这些网址可用性或真实机器验收已经被本脚本验证。

## Chrome Web Store 渠道

```powershell
python ShopController/scripts/publish_release.py --channel store --extension-id <正式商店ID> --dotnet <dotnet路径>
```

默认渠道仍为 `store`，保持旧命令兼容。商店上传 ZIP 删除 key。未传 ID 时生成待绑定助手，首次安装需要输入实际 ID；不使用测试 ID 冒充商店身份。此渠道的严格准备检查仍包含签名/真实机器验收待办。

## 源码与许可证

源包只包含三个产品目录，以及脚本中 `ROOT_SOURCE_FILES` 明确列出的仓库级 README、MIT LICENSE、贡献/安全说明、CI、公开网站文件。不会递归打包仓库根目录、`.git`、SDK、构建产物、原用户配置或私钥。新增根文件须主动加入白名单。产品许可同时随扩展和助手分发；.NET 的独立许可保存在 `runtime-notices`。

完整交付 ZIP 和 `SHA256SUMS.txt` 动态收录实际生成的交付 ZIP，因此 GitHub 渠道含六个 ZIP，商店渠道含五个。完整交付 ZIP 放在 `dist` 下，另有单独的 `.sha256`。所有交付构建均明确记录渠道、身份来源和未完成事项。
