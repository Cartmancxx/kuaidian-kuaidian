"""Build auditable Chrome-store and per-OS helper artifacts; never installs them."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
import zipfile
from urllib.parse import urlparse
from xml.etree import ElementTree

PRODUCT = Path(__file__).resolve().parents[1]
REPO = PRODUCT.parent
DIST = REPO / 'dist'
RIDS = ('win-x64', 'osx-arm64', 'osx-x64')
OMIT_DIRS = {'bin', 'obj', '__pycache__', 'verification', '.git', 'node_modules'}
ROOT_SOURCE_FILES = (
    'README.md', 'LICENSE', 'CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', '.gitignore', '.gitattributes',
    'global.json', 'NuGet.Config', 'package.json', 'package-lock.json', 'Directory.Build.props', 'Directory.Build.targets',
    '.github/workflows/ci.yml', '.github/workflows/ci.yaml',
    '.github/workflows/release.yml', '.github/workflows/release.yaml',
    '.github/workflows/pages.yml', '.github/workflows/pages.yaml',
    '.github/ISSUE_TEMPLATE/bug_report.md', '.github/ISSUE_TEMPLATE/feature_request.md',
    '.github/ISSUE_TEMPLATE/config.yml', '.github/PULL_REQUEST_TEMPLATE.md',
    'docs/index.html', 'docs/privacy.html', 'docs/style.css', 'docs/setup.css', 'docs/icon128.png',
    'docs/.nojekyll', 'docs/screenshot-launcher.jpg', 'docs/screenshot-manager.jpg',
)


def extension_id_from_key(key: str) -> str:
    """Chrome's stable unpacked ID: first 128 SHA-256 bits of the DER public key, a-p encoded."""
    if not isinstance(key, str) or not key:
        raise ValueError('GitHub releases require a fixed public manifest.key in the production extension.')
    try:
        decoded = base64.b64decode(key, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('manifest.key must be a base64-encoded DER public key.') from error
    if len(decoded) < 32 or decoded[0] != 0x30:
        raise ValueError('manifest.key does not contain a DER public key.')
    digest = hashlib.sha256(decoded).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(nibble, 16)) for nibble in digest)


def checked_dist(path: Path) -> Path:
    path = path.absolute()
    if path == DIST or not path.is_relative_to(DIST):
        raise ValueError(f'Output is outside the release directory: {path}')
    current = path
    while current != DIST.parent:
        if current.is_symlink() or (current.exists() and current.resolve() != current):
            raise ValueError(f'Redirected output path: {current}')
        current = current.parent
    return path


def files_below(root: Path, omit_dirs: set[str] | None = None):
    for file in sorted(root.rglob('*')):
        relative = file.relative_to(root)
        if omit_dirs and any(part in omit_dirs for part in relative.parts):
            continue
        if file.is_symlink():
            raise ValueError(f'Symlinks are not included in releases: {file}')
        if file.is_file():
            yield file, relative


def executable_archive_file(path: Path) -> bool:
    if path.suffix in ('.command', '.sh') or path.name == 'ShopController.Host':
        return True
    with path.open('rb') as stream:
        magic = stream.read(4)
    return magic in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')


def zip_tree(root: Path, destination: Path, prefix: str = '', omit_dirs: set[str] | None = None):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file, relative in files_below(root, omit_dirs):
            name = '/'.join(part for part in (prefix, relative.as_posix()) if part)
            info = zipfile.ZipInfo(name, time.localtime(max(file.stat().st_mtime, 315532800))[:6])
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | (0o755 if executable_archive_file(file) else 0o644)) << 16
            archive.writestr(info, file.read_bytes())


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', choices=('store', 'github'), default='store')
    parser.add_argument('--extension-id', default='')
    parser.add_argument('--dotnet', default='')
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--require-publish-ready', action='store_true')
    args = parser.parse_args()
    if args.skip_build and args.build_only:
        parser.error('--build-only and --skip-build are mutually exclusive')
    if args.extension_id and not re.fullmatch('[a-p]{32}', args.extension_id):
        parser.error('--extension-id must be the actual 32-letter Chrome Web Store ID (a-p).')
    manifest = json.loads((PRODUCT / 'extension/manifest.json').read_text(encoding='utf-8-sig'))
    public_key = manifest.get('key', '')
    github_id = extension_id_from_key(public_key) if args.channel == 'github' else None
    release_metadata_path = PRODUCT / 'release-config.json'
    release_metadata = json.loads(release_metadata_path.read_text(encoding='utf-8-sig')) if release_metadata_path.is_file() else {}
    configured_id = release_metadata.get('extensionId') or ''
    if configured_id and not re.fullmatch('[a-p]{32}', configured_id):
        raise ValueError('release-config.json contains an invalid extensionId')
    if args.channel == 'github' and args.extension_id:
        parser.error('--extension-id is for the store channel; GitHub helpers bind automatically to manifest.key.')
    if args.extension_id and configured_id and args.extension_id != configured_id:
        raise ValueError('Command-line extension ID differs from release-config.json')
    store_id = args.extension_id or configured_id
    binding_id = github_id if args.channel == 'github' else store_id
    identity_source = 'manifest-key' if args.channel == 'github' else ('chrome-web-store' if store_id else 'unbound')
    product_name = release_metadata.get('productName') or manifest['name']
    pending = []
    for field in ('publisherName', 'supportEmail'):
        if not release_metadata.get(field):
            pending.append('Missing ' + field)
    if release_metadata.get('supportEmail') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', release_metadata['supportEmail']):
        pending.append('Invalid supportEmail')
    for field in ('privacyPolicyUrl', 'downloadPageUrl'):
        parsed = urlparse(release_metadata.get(field) or '')
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
            pending.append('Missing or invalid public HTTPS ' + field)
    # This builder runs no signing or actual installation. Never infer readiness from a config flag.
    warnings = ['Windows signing verification pending', 'macOS Developer ID signing/notarization pending',
                'Clean Windows installation acceptance pending', 'Real Mac installation and Chrome routing acceptance pending']
    if args.channel == 'store':
        if not store_id:
            pending.append('Official Chrome Web Store extension ID is not bound')
        pending.extend(warnings)
    else:
        warnings.extend(['GitHub public beta uses Load unpacked in Chrome developer mode; enterprise policies may restrict it',
                         'Chrome Web Store approval is not implied by this GitHub release'])
        if not store_id:
            warnings.append('No Chrome Web Store ID has been assigned; it is not required for this manifest-key GitHub channel')
    if args.require_publish_ready and pending:
        raise ValueError(f'{args.channel} release metadata/readiness gate is closed:\n- ' + '\n- '.join(pending))
    version = str(manifest['version'])
    if not re.fullmatch(r'\d+(?:\.\d+){0,3}', version):
        raise ValueError('Invalid extension version')
    license_path = REPO / 'LICENSE'
    if args.channel == 'github' and not license_path.is_file():
        raise ValueError('GitHub source/binary distribution requires the repository LICENSE.')
    DIST.mkdir(exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    build = checked_dist(DIST / ('ShopController-build-' + version))
    build.mkdir(exist_ok=True)
    dotnet = args.dotnet or str(REPO / '.tools/dotnet10/dotnet.exe')
    if not Path(dotnet).is_file():
        dotnet = shutil.which('dotnet') or dotnet
    project = PRODUCT / 'host/ShopController.Host.csproj'
    project_xml = ElementTree.parse(project)
    target_framework = project_xml.findtext('.//TargetFramework')
    if project_xml.findtext('.//Version') != version or release_metadata.get('version', version) != version:
        raise ValueError('Host, extension, and release metadata versions must match.')
    if target_framework != 'net10.0':
        raise ValueError('Public helper releases require the reviewed net10.0 target.')
    environment = os.environ.copy()
    environment.update({'DOTNET_CLI_TELEMETRY_OPTOUT': '1', 'DOTNET_GENERATE_ASPNET_CERTIFICATE': 'false',
                        'DOTNET_CLI_HOME': str(REPO / '.tools/cli-home10')})
    sdk_version = subprocess.check_output([dotnet, '--version'], cwd=REPO, env=environment, text=True).strip()
    if not sdk_version.startswith('10.'):
        raise ValueError(f'The selected SDK does not match net10.0: {sdk_version}')
    source_hash = hashlib.sha256()
    for source_root in (PRODUCT / 'host', REPO / 'ShopController.Core'):
        for source_file, relative in files_below(source_root, OMIT_DIRS):
            if source_file.suffix in ('.cs', '.csproj'):
                source_hash.update((source_root.name + '/' + relative.as_posix()).encode('utf-8'))
                source_hash.update(source_file.read_bytes())
    build_source_hash = source_hash.hexdigest()

    # Publish sequentially: the projects share intermediate directories.
    for rid in RIDS:
        published = checked_dist(build / rid)
        provenance_path = checked_dist(build / (rid + '.build.json'))
        expected_provenance = {'runtime': rid, 'sdkVersion': sdk_version, 'targetFramework': target_framework,
                               'sourceHash': build_source_hash}
        if args.skip_build:
            if not provenance_path.is_file() or json.loads(provenance_path.read_text(encoding='utf-8')) != expected_provenance:
                raise ValueError(f'Cached {rid} build does not match current host/core sources; rebuild without --skip-build.')
        else:
            if published.exists():
                backup = checked_dist(build / (rid + '.previous-' + stamp))
                published.rename(backup)  # preserve old binaries; no recursive delete
            subprocess.run([dotnet, 'publish', str(project), '-c', 'Release', '-r', rid,
                            '--self-contained', 'true', '-o', str(published),
                            '-p:PublishSingleFile=true', '-p:PublishTrimmed=false',
                            '-p:DebugType=None', '-p:DebugSymbols=false'], cwd=REPO, env=environment, check=True)
            write_json(provenance_path, expected_provenance)
        expected = published / ('ShopController.Host.exe' if rid.startswith('win-') else 'ShopController.Host')
        if not expected.is_file():
            raise FileNotFoundError(f'Missing built helper: {expected}')
    if args.build_only:
        print(f'Builds ready: {build}')
        print('No release package, installer, registration, or browser was executed.')
        return

    stage = checked_dist(DIST / ('.ShopController-release-stage-' + stamp))
    stage.mkdir()
    (stage / '.shopcontroller-release-output').write_text(version, encoding='ascii')

    # The uploaded ZIP contains only extension assets, with manifest at its root.
    extension_stage = stage / 'extension-store'
    extension_stage.mkdir()
    for file, relative in files_below(PRODUCT / 'extension'):
        if relative.name in ('demo.js', 'extension-id.json') or relative.suffix in ('.map', '.psd'):
            continue
        destination = extension_stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, destination)
    manifest.pop('key', None)
    write_json(extension_stage / 'manifest.json', manifest)
    if license_path.is_file():
        shutil.copy2(license_path, extension_stage / 'LICENSE.txt')
    info_path = extension_stage / 'release-info.json'
    release_info = json.loads(info_path.read_text(encoding='utf-8-sig')) if info_path.is_file() else {}
    for field in ('productName', 'publisherName', 'supportEmail', 'privacyPolicyUrl', 'downloadPageUrl'):
        release_info[field] = release_metadata.get(field) or ''
    write_json(info_path, release_info)
    # Production code should never silently fall back to fixture accounts.
    for js, _ in files_below(extension_stage):
        if js.suffix == '.js' and re.search(r"(?:import\s*\(|from\s*)['\"][^'\"]*demo\.js", js.read_text(encoding='utf-8')):
            raise ValueError(f'Production source still imports demo.js: {js.name}')
    zip_tree(extension_stage, stage / f'ShopController-extension-{version}.zip')
    if args.channel == 'github':
        unpacked_stage = stage / 'extension-unpacked'
        shutil.copytree(extension_stage, unpacked_stage)
        unpacked_manifest = dict(manifest, key=public_key)
        write_json(unpacked_stage / 'manifest.json', unpacked_manifest)
        zip_tree(unpacked_stage, stage / f'ShopController-extension-unpacked-{version}.zip')

    package_records = []
    for rid in RIDS:
        published = checked_dist(build / rid)
        list(files_below(published))  # refuse symlinks before copytree follows any input
        bundle = stage / ('ShopController-' + rid)
        bundle.mkdir()
        shutil.copytree(published, bundle / 'host')
        if license_path.is_file():
            shutil.copy2(license_path, bundle / 'LICENSE.txt')
            shutil.copy2(license_path, bundle / 'host/LICENSE.txt')
        notices = bundle / 'runtime-notices'
        notices.mkdir()
        for notice_name in ('LICENSE.txt', 'ThirdPartyNotices.txt'):
            notice_source = Path(dotnet).resolve().parent / notice_name
            if not notice_source.is_file():
                raise FileNotFoundError(f'Required .NET redistribution notice missing: {notice_source}')
            shutil.copy2(notice_source, notices / notice_name)
        config = {'product': 'ShopController', 'version': version, 'runtime': rid,
                  'displayName': product_name,
                  'targetFramework': target_framework, 'sdkVersion': sdk_version,
                  'minimumMacOS': '15.0' if rid.startswith('osx-') else None,
                  'supportedWindows': 'Windows 11 x64, vendor-supported releases' if rid.startswith('win-') else None,
                  'channel': args.channel, 'identitySource': identity_source,
                  'extensionId': binding_id or None, 'bindingStatus': 'bound' if binding_id else 'unbound',
                  'signed': False, 'notarized': False}
        write_json(bundle / 'release-config.json', config)
        source = PRODUCT / 'scripts/release' / ('windows' if rid.startswith('win-') else 'macos')
        for script, relative in files_below(source):
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(script, target)
        zip_name = f'ShopController-helper-{version}-{rid}.zip'
        zip_tree(bundle, stage / zip_name, prefix=bundle.name)
        package_records.append({'file': zip_name, **config})

    # Include reproducible product sources, never the unrelated repository project.
    source_zip = stage / f'ShopController-source-{version}.zip'
    with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in ('ShopController', 'ShopController.Core', 'ShopController.Tests'):
            for file, relative in files_below(REPO / name, OMIT_DIRS):
                if file.suffix in ('.pyc', '.pfx', '.p12', '.pem', '.key') or file.name in ('config.json', 'host-identity.json'):
                    continue
                info = zipfile.ZipInfo(name + '/' + relative.as_posix())
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | (0o755 if executable_archive_file(file) else 0o644)) << 16
                if name == 'ShopController' and relative.as_posix() == 'release-config.json':
                    public_fields = ('productName', 'version', 'publisherName', 'supportEmail', 'privacyPolicyUrl',
                                     'downloadPageUrl', 'extensionId', 'windowsSigned', 'macNotarized',
                                     'windowsSmokeTested', 'macSmokeTested')
                    source_metadata = {key: release_metadata[key] for key in public_fields if key in release_metadata}
                    archive.writestr(info, json.dumps(source_metadata, ensure_ascii=False, indent=2).encode('utf-8'))
                else:
                    archive.writestr(info, file.read_bytes())
        for relative in ROOT_SOURCE_FILES:
            file = REPO / relative
            if not file.exists():
                continue
            if not file.is_file() or file.is_symlink() or file.resolve() != file.absolute():
                raise ValueError(f'Redirected or non-file root source entry: {relative}')
            info = zipfile.ZipInfo(relative)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, file.read_bytes())
    # Optional public submission material is authored separately by the product owner.
    for dirname in ('store', 'release-materials'):
        if (PRODUCT / dirname).is_dir():
            shutil.copytree(PRODUCT / dirname, stage / dirname)
    write_json(stage / 'release-manifest.json', {
        'version': version, 'channel': args.channel, 'identitySource': identity_source,
        'extensionId': binding_id or None, 'storeExtensionId': store_id or None,
        'githubExtensionId': github_id, 'distributionStatus': 'public-beta-build' if args.channel == 'github' else 'store-submission-build',
        'storeApproval': 'not-submitted', 'macRuntimeTest': 'not-performed-on-this-windows-host',
        'signatureStatus': 'unsigned', 'packages': package_records, 'pendingReleaseRequirements': pending,
        'productName': product_name, 'warnings': warnings,
    })
    if args.channel == 'github':
        binding = f'''GitHub 公开测试渠道：助手已绑定生产扩展公开 manifest.key 对应的固定 ID：`{binding_id}`。
该 ID 来自公开 key 的 SHA-256，不是商店审核结果，也不是软件签名；请保持 key 不变，避免升级后身份改变。
未分配商店 ID 不影响此 GitHub 渠道。不要将无 key 的商店上传 ZIP 当作此渠道的加载包。'''
        channel_instructions = f'''1. 解压 `ShopController-extension-unpacked-{version}.zip` 到准备长期保留的文件夹。
2. 在 Chrome 的 `chrome://extensions` 打开“开发者模式”，选择“加载已解压的扩展程序”，选择包含 manifest.json 的文件夹。
3. 确认扩展 ID 为 `{binding_id}`，再解压对应系统的助手 ZIP，运行 Install.cmd（Windows）或 Install.command（Mac）。助手包已自动绑定，不需要手填 ID。
4. 打开扩展并选择重试连接。组织策略可能限制开发者模式；请保留设备的正常安全防护，不绕过组织策略。
5. 更新 GitHub 测试版时，备份配置、关闭控制器，以新版扩展替换原文件夹内容并在扩展页点“重新加载”，然后运行新版助手安装器。此渠道没有商店自动更新。'''
        unpacked_bullet = f'- `ShopController-extension-unpacked-{version}.zip`：GitHub 测试版生产扩展，根 manifest 保留固定公开 key，无演示模块。\n'
        channel_status = '这是可分发的 GitHub 公开测试构建，不代表商店已上架、操作系统签名已完成或真实 Mac 验收已通过。签名与真实机器验收是已公开的测试版限制，不阻止此渠道产物生成。'
    else:
        binding = ('已绑定正式扩展 ID：' + store_id) if store_id else '尚未绑定正式商店扩展 ID；安装助手时需输入实际 ID。'
        channel_instructions = '首次上传无 key 的扩展 ZIP 后，在商店开发者控制台读取正式 ID，再执行 `publish-release.ps1 -Channel store -ExtensionId <实际ID>` 生成已绑定助手。安装器把此 ID 同时写入宿主身份文件与 Chrome 白名单。任何测试 ID 均不得冒充正式 ID。'
        unpacked_bullet = ''
        channel_status = '这是商店提交渠道的构建交付，尚未提交商店，也没有宣称已通过审核。公开商店发行前请完成身份绑定、签名和真实机器验收。'
    (stage / '交付说明.md').write_text(f'''# {product_name} {version} 发布交付

## 包的用途
{unpacked_bullet}
- `ShopController-extension-{version}.zip`：仅扩展，manifest 位于 ZIP 根目录，供 Chrome Web Store 上传；不含开发 key 或演示账号模块。
- `ShopController-helper-{version}-win-x64.zip`：Windows 用户级助手，解压后运行 Install.cmd。
- `ShopController-helper-{version}-osx-arm64.zip`：Apple Silicon Mac 助手。
- `ShopController-helper-{version}-osx-x64.zip`：Intel Mac 助手。
- `ShopController-source-{version}.zip`：本产品源码、测试、MIT LICENSE 及白名单内的开源文档/CI；不含原用户配置、开发 SDK 或无关项目。
- `SHA256SUMS.txt`：所有交付 ZIP 的摘要。

## 身份与首次绑定
{binding}

## 安装与更新
{channel_instructions}

## 当前发布状态
{channel_status}

Windows 签名、Mac Developer ID 签名/公证、Mac 真实机器安装启动测试仍需完成。系统可能阻止未签名或未公证的程序，尤其 Mac；无需也不应关闭系统防护来测试。macOS 提供 `Sign-And-Notarize.sh` 供持有者在 Mac 上使用自己的凭据；构建不执行签名、不登记助手、不启动 Chrome。Mac 使用普通独立小窗，不做置顶。

首次安装只登记本地助手；扩展根据所选渠道由用户加载测试版或从商店安装。Cookie、密码及真实店铺配置不随包分发。

## 渠道待办
{chr(10).join('- ' + item for item in pending) or '- 本渠道必需元数据已提供；以下测试版限制仍然适用。'}

## 已知限制与警告
{chr(10).join('- ' + item for item in warnings)}

本产品按随包 MIT LICENSE 发布。各助手包的 runtime-notices 单独保存所带 .NET 运行时的许可证与第三方通知，不能将两者混为一份许可。
''', encoding='utf-8')
    hashes = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in sorted(stage.glob('*.zip'))]
    (stage / 'SHA256SUMS.txt').write_text('\n'.join(hashes) + '\n', encoding='ascii')
    output = checked_dist(DIST / ('ShopController-release-' + version))
    if output.exists():
        if not (output / '.shopcontroller-release-output').is_file():
            raise ValueError(f'Existing output has no build marker; preserving it: {output}')
        output.rename(checked_dist(DIST / (output.name + '.previous-' + stamp)))
    stage.rename(output)
    # A compact hand-off archive includes compressed deliverables, not their duplicate extracted trees.
    delivery = checked_dist(DIST / f'快店快点-{version}-完整交付.zip')
    delivery_stage = checked_dist(DIST / f'.ShopController-delivery-{stamp}.zip')
    with zipfile.ZipFile(delivery_stage, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        selected = [p for p in sorted(output.glob('*.zip'))]
        selected += [output / name for name in ('交付说明.md', 'release-manifest.json', 'SHA256SUMS.txt')]
        if (output / 'store').is_dir():
            selected += [file for file, _ in files_below(output / 'store')]
        for file in selected:
            archive.write(file, file.relative_to(output).as_posix(),
                          compress_type=zipfile.ZIP_STORED if file.suffix == '.zip' else zipfile.ZIP_DEFLATED)
    if delivery.exists():
        delivery.rename(checked_dist(DIST / f'快店快点-{version}-完整交付.previous-{stamp}.zip'))
    delivery_stage.rename(delivery)
    digest = hashlib.sha256(delivery.read_bytes()).hexdigest()
    checked_dist(DIST / (delivery.name + '.sha256')).write_text(f'{digest}  {delivery.name}\n', encoding='utf-8')
    print(f'Release directory: {output}')
    print(f'Complete delivery: {delivery}')
    print(f'Channel: {args.channel}; identity source: {identity_source}')
    print(f'Identity binding: {binding_id or "UNBOUND - requires actual store ID"}')
    print('No installer, registration, native window, or browser was executed.')


if __name__ == '__main__':
    main()
