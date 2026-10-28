namespace ShopController.Core;

public static class PlatformCatalog
{
    public static string GetLabel(ShopPlatform platform) => platform switch
    {
        ShopPlatform.JD => "京东",
        ShopPlatform.Taobao => "淘宝",
        ShopPlatform.Tmall => "天猫",
        ShopPlatform.Pdd => "拼多多",
        _ => "其他"
    };

    public static string GetRealm(ShopPlatform platform) => platform switch
    {
        ShopPlatform.JD => "JD",
        ShopPlatform.Taobao or ShopPlatform.Tmall => "Alibaba",
        ShopPlatform.Pdd => "Pdd",
        _ => "Other"
    };

    // These are entry-point suggestions only. Shops may use their own HTTPS URL.
    public static string GetDefaultUrl(ShopPlatform platform) => platform switch
    {
        ShopPlatform.JD => "https://shop.jd.com/",
        ShopPlatform.Taobao or ShopPlatform.Tmall => "https://myseller.taobao.com/",
        ShopPlatform.Pdd => "https://mms.pinduoduo.com/",
        _ => ""
    };
}
