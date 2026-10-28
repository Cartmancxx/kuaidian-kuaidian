using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace ShopController.Host;

/// <summary>
/// Pins only the native caller window supplied by Chrome on the host command line.
/// No window handle, process ID, title, or executable is accepted from message JSON.
/// </summary>
internal static class WindowPinning
{
    private const string ParentArgumentPrefix = "--parent-window=";
    private const uint GaRoot = 2;
    private const int GwlExStyle = -20;
    private const long WsExTopmost = 0x00000008L;
    private const uint SwpNoSize = 0x0001;
    private const uint SwpNoMove = 0x0002;
    private const uint SwpNoActivate = 0x0010;

    /// <summary>Pure parser: missing, duplicate, signed, hex, or overflowing values fail closed.</summary>
    internal static nint ParseParentHandle(IEnumerable<string> arguments)
    {
        var candidates = arguments.Where(arg => arg.StartsWith(ParentArgumentPrefix, StringComparison.Ordinal)).ToArray();
        if (candidates.Length != 1) return 0;
        var value = candidates[0][ParentArgumentPrefix.Length..];
        if (value.Length == 0 || value.Any(c => c is < '0' or > '9') ||
            !ulong.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var numeric) || numeric == 0)
            return 0;
        var maximum = IntPtr.Size == 8 ? (ulong)long.MaxValue : int.MaxValue;
        return numeric <= maximum ? (nint)numeric : 0;
    }

    internal static bool GetPinned(nint parentWindow) => ReadPinned(ValidateCallerWindow(parentWindow));

    internal static bool SetPinned(nint parentWindow, bool enabled)
    {
        var window = ValidateCallerWindow(parentWindow);
        var insertAfter = enabled ? new nint(-1) : new nint(-2); // HWND_TOPMOST / HWND_NOTOPMOST
        if (!SetWindowPos(window, insertAfter, 0, 0, 0, 0, SwpNoSize | SwpNoMove | SwpNoActivate))
            throw new Win32Exception(Marshal.GetLastWin32Error(), "小窗置顶设置未成功，请重试。");

        // Check again in case the caller window closed while the native request was running.
        var confirmedWindow = ValidateCallerWindow(parentWindow);
        if (confirmedWindow != window)
            throw new InvalidOperationException("调用窗口已变化，置顶状态尚未确认。");
        var actual = ReadPinned(window);
        if (actual != enabled)
            throw new InvalidOperationException("系统未确认所请求的置顶状态，请重试。");
        return actual;
    }

    private static nint ValidateCallerWindow(nint parentWindow)
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("小窗置顶仅支持 Windows。");
        if (parentWindow == 0)
            throw new InvalidOperationException("此请求没有 Chrome 小窗句柄。请从独立店铺小窗直接操作置顶按钮。");
        if (!IsWindow(parentWindow)) throw new InvalidOperationException("调用小窗已关闭，请重新打开。");
        var root = GetAncestor(parentWindow, GaRoot);
        if (root == 0 || !IsWindow(root)) throw new InvalidOperationException("未找到有效的 Chrome 顶层窗口。");
        var className = new StringBuilder(256);
        if (GetClassName(root, className, className.Capacity) == 0 || className.ToString() != "Chrome_WidgetWin_1")
            throw new InvalidOperationException("调用窗口不是受支持的 Chrome 窗口，未修改置顶状态。");
        if (GetWindowThreadProcessId(root, out var processId) == 0 || processId == 0)
            throw new InvalidOperationException("未识别调用窗口的 Chrome 进程。");
        using var process = Process.GetProcessById(checked((int)processId));
        var executable = process.MainModule?.FileName;
        if (!string.Equals(process.ProcessName, "chrome", StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(Path.GetFileName(executable), "chrome.exe", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("调用窗口不属于 chrome.exe，未修改置顶状态。");
        return root;
    }

    private static bool ReadPinned(nint window)
    {
        Marshal.SetLastPInvokeError(0);
        var style = IntPtr.Size == 8 ? GetWindowLongPtr(window, GwlExStyle).ToInt64() : GetWindowLong(window, GwlExStyle);
        var error = Marshal.GetLastWin32Error();
        if (style == 0 && error != 0)
            throw new Win32Exception(error, "未读取到实际置顶状态。");
        return (style & WsExTopmost) != 0;
    }

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindow(nint hWnd);

    [DllImport("user32.dll")]
    private static extern nint GetAncestor(nint hWnd, uint gaFlags);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetClassNameW", SetLastError = true)]
    private static extern int GetClassName(nint hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out uint processId);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetWindowPos(nint hWnd, nint hWndInsertAfter, int x, int y, int cx, int cy, uint flags);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
    private static extern nint GetWindowLongPtr(nint hWnd, int index);

    [DllImport("user32.dll", EntryPoint = "GetWindowLongW", SetLastError = true)]
    private static extern int GetWindowLong(nint hWnd, int index);
}
