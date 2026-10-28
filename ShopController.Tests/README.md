# ShopController 自动化测试

核心项目是无额外测试框架依赖的 .NET 8 控制台测试程序，助手使用 .NET 10。
推荐安装系统级 **.NET 10 SDK 和 .NET 8 运行时**；也可安装 .NET 10 与 .NET 8 两套 SDK，
后者会一并提供测试所需的运行时。Node.js 22+、Python 3.10+ 用于其他自动化检查。
仓库的 global.json 选择 .NET 10 SDK；不要从仅含 .NET 8 的私有 SDK 目录启动构建。

在仓库根目录运行：

```powershell
dotnet build ShopController/host/ShopController.Host.csproj -c Release
dotnet run --project ShopController.Tests/ShopController.Tests.csproj -c Release
```

仓库不分发开发 SDK，`dotnet` 应来自系统 PATH。正式助手包自带 .NET 10 运行时，用户安装助手时不需要安装开发 SDK。

测试范围：

- 京东、淘宝/天猫、PDD 等登录域的资料分配、跨平台复用、容量不足与绑定稳定性。
- 店铺字段、网址、资料目录的输入验证。
- 配置读写、前一版本备份、坏 JSON 和未知版本防覆盖。
- Chrome 参数逐项传递，以及临时 `Local State` 中的资料名称发现。

测试只使用系统临时目录下的随机测试目录，结束后清理该目录。
测试中 Chrome 程序是文本占位文件，仅供参数构造校验；Mac 样本使用 `.app/Contents/MacOS/Google Chrome`
路径和可执行位，但从不运行该文件。
**测试不启动 Chrome、不访问网络、不读取真实用户资料、Cookie 或密码。**

全部通过返回退出码 `0`；任何失败返回 `1`。

## Native Messaging 协议集成测试

```powershell
python .\ShopController.Tests\protocol_tests.py
```

该脚本自动编译 `ShopController.Host`，然后通过标准输入/输出交换真实的
4 字节小端长度前缀及 UTF-8 JSON 消息。已编译时可加 `--no-build`。

覆盖配置修订冲突、添加/删除店铺、限制参与配对的资料池、计划令牌与资料变化检测、
配对应用、精确启动参数、持久化重启、畸形消息、超大响应/保存限制和来源校验。
测试先规范化临时样本根目录，避免 Windows CI 的 TEMP 8.3 短名称与 .NET 完整路径拼写不一致；
启动参数仍按完整三元素数组严格比较（含完整资料根目录、资料名与原始 URL），失败会显示期望值和实际值，
不使用子串匹配放宽参数边界。

所有实例使用 `--protocol-test` 和预置的临时配置；`open_shop` 仅生成启动参数，
不执行浏览器。测试不会注册 Native Messaging host，也不读取真实默认 Chrome 资料。

## 小窗生命周期模拟测试

运行 `node .\ShopController.Tests\launcher_tests.cjs`，验证紧凑独立窗口、单实例、
service worker 重启后的窗口复用、最小化恢复、来源限制及失败重试。
所有 Chrome API 均为内存模拟，不安装扩展或访问真实窗口。

## 正式版兼容性与身份检查

Python 脚本从助手项目读取目标框架，默认使用系统 `dotnet`。
若开发者自己提供了 `.tools/dotnet10` 或 `.tools/dotnet`，脚本也能检测这些本地路径；
它们不是源码包的一部分，所选 SDK 必须满足 global.json 的 .NET 10 要求。
上面的独立核心测试使用 .NET 8 运行时；正式助手自身不依赖 .NET 8 运行时。

```powershell
python .\ShopController.Tests\identity_tests.py
python .\ShopController.Tests\pinning_tests.py
python .\ShopController.Tests\platform_tests.py
python .\ShopController.Tests\installer_tests.py
node .\ShopController.Tests\api_tests.cjs
node .\ShopController.Tests\default_pin_tests.cjs
node .\ShopController.Tests\launcher_tests.cjs
node .\ShopController.Tests\setup_tests.cjs
```

- `identity_tests.py`：复制编译结果到随机临时目录，用临时身份文件运行正常来源验证。
  只发送 `get_capabilities`，它在读取配置和发现资料之前响应；验证错误身份拒绝、
  正式 ID 精确匹配，以及版本/平台能力。不接触已安装助手或真实 Chrome 资料。
- `pinning_tests.py`：纯窗口参数解析、协议字段边界与坏配置保留；不调用窗口系统 API。
- `platform_tests.py`：平台路径、资料参数、版本、原子配置和备份检查。
  Mac 执行权限和文件 0600 检查仅在真正的 Mac 上执行。
- `installer_tests.py`：只运行安装参数、ID、产品路径和注册归属判断的纯函数；静态检查 CLI 与扩展消息隔离。
  不调用安装/卸载方法，不读取注册表，不创建真实安装目录。
- `api_tests.cjs`：生产版本禁用演示入口，握手缓存、版本兼容和失败恢复均使用内存模拟。
- `default_pin_tests.cjs`：Windows 首次置顶、手动取消、失败状态和 Mac 不置顶，DOM/API 全部模拟。
- `launcher_tests.cjs`：常驻小窗生命周期、服务进程重启恢复，以及扩展来源/操作白名单。
- `setup_tests.cjs`：本地元数据、HTTPS 下载链接、真实扩展 ID、Mac 提示和连接失败重试；不访问网络或真实剪贴板。

身份测试会明确报告临时文件清理受系统拒绝的情况，并保留路径；不会因此忽略测试断言失败。

## 分发压缩包检查

公开源码提交前运行：

```powershell
python ShopController.Tests/public_source_tests.py
python ShopController.Tests/release_policy_tests.py
```

前者只扫描本仓库源码，对疑似秘密仅报告位置、不输出值；已配置的公开支持邮箱和保留 example 域样本会放行。
它是启发式检查，不是所有秘密都能被自动发现的保证。后者检查公开 key 的 ID 派生、非法 key 拒绝、MIT 许可与构建文件白名单，不构建或发布。

在生成交付目录后运行：

```powershell
python .\ShopController.Tests\distribution_tests.py .\dist\ShopController-release-1.0.0
```

检查商店 ZIP 的根清单、权限、图标、正式代码，三个助手包的架构/安装入口/运行时通知，
Mac 执行位和行尾，源码排除规则，以及所有 ZIP 的 SHA-256。
检查过程仅读取压缩包，不解压、不安装、不运行里面的软件。

分发检查区分 store 与 github 渠道。GitHub 包保留固定公开 manifest.key，
测试会独立计算扩展 ID，并核对助手绑定；并存的商店投稿 ZIP 仍去掉该 key。
GitHub 渠道无需预先分配商店 ID，但未签名、未公证和尚未完成实机联调的状态必须如实保留。

Windows 上可另外运行 `python .\ShopController.Tests\packaged_host_tests.py .\dist\ShopController-release-1.0.0`。
这项检查将 Windows 助手解压到独立临时目录，只运行正常来源下的 `get_capabilities`，
检查发布后的自包含程序能否启动、身份拒绝和版本帧；不调用安装入口，不登记注册表，不读取浏览器资料。

## 自动化检查的边界

这些检查不等同于商店审核、代码签名、公证或真实机器验收。仍需在独立 Windows 和 Mac
环境中验证安装、更新、卸载、真实 Chrome 打开资料、登录身份、小窗行为和扩展兼容。
自动化测试不启动浏览器、不读取 Cookie/密码、不注册本地助手，也不改注册表。
