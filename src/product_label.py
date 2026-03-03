import re
from dataclasses import dataclass

from src.analyzer import DealLine, RankedStore


@dataclass
class ProductInfo:
    label_cn: str
    est_cost: str | None = None
    est_cost_usd: float | None = None


KNOWN_STORES: dict[str, ProductInfo] = {
    "Namecheap": ProductInfo("域名注册 & 网站托管", "$10-50/年", 30),
    "Bluehost": ProductInfo("WordPress 网站托管", "$36-480/年(独服更贵)", 200),
    "HostGator": ProductInfo("网站托管服务", "$36-300/年", 100),
    "GoDaddy.com": ProductInfo("域名 & 网站托管", "$12-300/年", 80),
    "Ultra Web Hosting": ProductInfo("网站托管服务", "$24-120/年", 60),
    "Network Solutions": ProductInfo("域名 & 网站托管", "$10-200/年", 80),
    "CyberGhost": ProductInfo("VPN 隐私保护", "$2-13/月", 50),
    "NordVPN": ProductInfo("VPN 隐私保护", "$4-15/月", 70),
    "Surfshark": ProductInfo("VPN & 网络安全", "$2-16/月", 50),
    "PureVPN": ProductInfo("VPN 隐私保护", "$2-11/月", 40),
    "Private Internet Access": ProductInfo("VPN 隐私保护", "$2-12/月", 40),
    "WiTopia": ProductInfo("VPN 隐私保护", "$4-12/月", 60),
    "Proton": ProductInfo("加密邮箱 & VPN & 云存储", "$4-13/月", 60),
    "Easyship": ProductInfo("跨境电商物流平台", "免费/按量计费", 0),
    "Skylum": ProductInfo("AI 照片编辑软件 (Luminar)", "$10-15/月", 120),
    "Bitdefender": ProductInfo("杀毒/网络安全软件", "$30-100/年", 50),
    "AmeriCommerce": ProductInfo("电商建站平台", "$25-300/月", 200),
    "CapCut": ProductInfo("视频编辑软件 (剪映国际版)", "$8-14/月", 100),
    "Upwork": ProductInfo("自由职业者接单平台", "按项目计费", None),
    "Elementor": ProductInfo("WordPress 页面编辑器", "$59-399/年", 100),
    "MacKeeper": ProductInfo("Mac 系统优化工具", "$72-144/年", 72),
    "IObit": ProductInfo("PC 系统优化工具", "$17-45/年", 30),
    "LastPass": ProductInfo("密码管理器", "$36-48/年", 36),
    "MacPaw": ProductInfo("Mac 工具软件 (CleanMyMac)", "$30-90/年", 50),
    "EaseUS": ProductInfo("数据恢复/备份软件", "$70-150/年", 80),
    "AOMEI": ProductInfo("磁盘分区/备份软件", "$40-70", 50),
    "MiniTool": ProductInfo("数据恢复/磁盘管理", "$69-99", 80),
    "Placeit": ProductInfo("Logo/设计模板平台", "$8-15/月", 100),
    "Clip Studio Paint": ProductInfo("漫画/插画绘图软件", "$22-52/年", 35),
    "PDF Expert": ProductInfo("PDF 编辑工具", "$80/年", 80),
    "AirDroid": ProductInfo("手机远程管理工具", "$20-40/年", 30),
    "HitPaw": ProductInfo("AI 视频/图片编辑", "$36-66/年", 50),
    "DocuEase": ProductInfo("文档管理软件", "$10-30/月", 100),
    "Manychat": ProductInfo("聊天机器人/自动化营销", "$15-45/月", 200),
    "QuickBooks": ProductInfo("企业记账/财务软件", "$200-1800/年", 500),
    "TurboTax": ProductInfo("报税软件", "$0-130/次", 70),
    "SignNow": ProductInfo("电子签名服务", "$120-600/年(API更贵)", 300),
    "The Motley Fool": ProductInfo("投资建议/股票分析订阅", "$199-13999/年", 1000),
    "Xendoo": ProductInfo("在线记账服务", "$200-600/月", 3000),
    "SentryPC": ProductInfo("电脑监控/家长控制软件", "$60-1000+", 200),
    "Rebag": ProductInfo("二手奢侈品包包交易", "$500-15000+", 5000),
    "TopResume": ProductInfo("简历代写服务", "$149-499", 250),
    "Verizon Business": ProductInfo("企业通信/网络服务", "$35-400/月", 200),
    "Jobber": ProductInfo("现场服务管理软件", "$39-249/月", 150),
    "eReleases": ProductInfo("新闻稿发布服务", "$300-500/次", 400),
    "Discover Cars": ProductInfo("租车比价平台", "按租期", None),
    "Ticket Club": ProductInfo("演出/体育赛事门票", "按活动", None),
    "mSpy": ProductInfo("手机监控软件", "$30-70/月", 50),
    "Nektony (MacCleaner)": ProductInfo("Mac 清理工具", "$25-45", 35),
    "SurePayroll": ProductInfo("小企业工资管理", "$20-60/月", 300),
    "BetterLegal": ProductInfo("公司注册/LLC 成立服务", "$299", 299),
    "AT&T Business": ProductInfo("企业通信/网络服务", "$50-250/月", 150),
    "Square": ProductInfo("支付终端/POS 系统", "免费-$60/月+手续费", 100),
    "ZipRecruiter": ProductInfo("招聘平台", "$249-999/月", 500),
    "Constant Contact": ProductInfo("邮件营销平台", "$12-80/月", 200),
    "GoToWebinar": ProductInfo("在线研讨会平台", "$59-399/月", 200),
    "GoToMyPC": ProductInfo("远程桌面软件", "$35-45/月", 400),
    "HughesNet": ProductInfo("卫星宽带网络", "$50-150/月", 100),
    "PassFab": ProductInfo("密码恢复工具", "$16-50", 30),
    "ClevGuard": ProductInfo("手机监控软件", "$30-50/月", 40),
    "iMobie": ProductInfo("iOS 数据管理工具", "$40-60", 50),
    "Systweak Software": ProductInfo("PC 优化工具", "$40-60/年", 50),
    "K7 Computing": ProductInfo("杀毒软件", "$20-40/年", 30),
    "Advanced System Repair": ProductInfo("PC 修复工具", "$30-50", 40),
    "BusinessWatch Network": ProductInfo("商业资讯订阅", "$20-50/月", 200),
    "O&O Software": ProductInfo("Windows 系统工具", "$30-50", 40),
    "DRmare": ProductInfo("DRM 解除/音频转换", "$30-50", 40),
    "MagFone": ProductInfo("屏幕解锁/数据恢复", "$40-60", 50),
    "Audials": ProductInfo("流媒体录制软件", "$30-60", 45),
}

CATEGORY_CN: dict[str, str] = {
    "web": "互联网服务",
    "computers-electronics-software": "软件工具",
    "financial-services": "金融服务",
    "business-career": "商务工具",
    "services": "在线服务",
    "Software": "软件工具",
    "Media": "媒体工具",
    "travel": "旅行服务",
    "style-apparel": "时尚服饰",
    "extra-cashback-brands": None,
}

_DOLLAR_RE = re.compile(r'\$[\d,]+(?:\.\d+)?')


def get_info(name: str) -> ProductInfo | None:
    return KNOWN_STORES.get(name)


def get_label(dl: DealLine) -> str:
    info = KNOWN_STORES.get(dl.store_name)
    if info:
        return info.label_cn

    cats = dl.store_item_categories or []
    cn_cats = [CATEGORY_CN[c] for c in cats if c in CATEGORY_CN and CATEGORY_CN[c]]
    if cn_cats:
        return " / ".join(dict.fromkeys(cn_cats))

    if dl.store_description:
        first_sentence = re.split(r'[.!]', dl.store_description, maxsplit=1)[0].strip()
        return first_sentence[:80]

    return dl.store_category


def extract_cost_from_product_name(product_name: str) -> float | None:
    matches = _DOLLAR_RE.findall(product_name)
    if matches:
        amounts = [float(m.replace("$", "").replace(",", "")) for m in matches]
        return max(amounts)
    return None


def estimate_cost(dl: DealLine) -> tuple[str | None, float | None]:
    name_cost = extract_cost_from_product_name(dl.product_name)
    if name_cost is not None:
        return f">${name_cost:,.0f}(产品名标注)", name_cost

    info = KNOWN_STORES.get(dl.store_name)
    if info and info.est_cost:
        return info.est_cost, info.est_cost_usd

    return None, None


def assess_flat_deal(
    dl: DealLine,
    mile_value_dollars: float,
) -> str:
    cost_str, cost_usd = estimate_cost(dl)

    if cost_usd is not None and cost_usd > 0:
        ratio = mile_value_dollars / cost_usd
        if ratio > 2.0:
            return f"💰 里程价值${mile_value_dollars:,.0f} vs 成本{cost_str} → 非常划算"
        elif ratio > 0.8:
            return f"👍 里程价值${mile_value_dollars:,.0f} vs 成本{cost_str} → 可以考虑"
        elif ratio > 0.3:
            return f"⚠️ 里程价值${mile_value_dollars:,.0f} vs 成本{cost_str} → 性价比一般"
        else:
            return f"❌ 里程价值${mile_value_dollars:,.0f} vs 成本{cost_str} → 太贵，不建议纯买点数"

    if cost_str:
        return f"里程价值${mile_value_dollars:,.0f} | 参考成本{cost_str}"

    return f"里程价值${mile_value_dollars:,.0f} | 成本未知"


def get_product_label(store: RankedStore) -> str:
    info = KNOWN_STORES.get(store.name)
    if info:
        return info.label_cn

    cats = store.item_categories or []
    cn_cats = [CATEGORY_CN[c] for c in cats if c in CATEGORY_CN and CATEGORY_CN[c]]
    if cn_cats:
        return " / ".join(dict.fromkeys(cn_cats))

    if store.description:
        first_sentence = re.split(r'[.!]', store.description, maxsplit=1)[0].strip()
        return first_sentence[:80]

    return store.category
