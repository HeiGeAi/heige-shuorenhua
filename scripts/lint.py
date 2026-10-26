#!/usr/bin/env python3
"""说人话 skill 的确定性检查：Blake 的硬规则和常见 AI 腔。

用法：
  python3 lint.py <文件或-> [--mode article|koubo|subtitle]
  文件可以是 .md / .txt / script.json（读出所有字符串）。传 - 从标准输入读。
  article（默认）：公众号、小红书、文档、回复
  koubo：口播稿，加查克隆声音风险字和中文数字
  subtitle：字幕，加查标点（字幕不放标点）

退出码：有错误项为 1，只有警告为 0。
脚本只查能机械判断的部分；语义（有没有增删事实、语气对不对）要靠回读。
代码块、行内代码、URL、文件路径、YAML front matter 不检查。
"""
import argparse, json, re, sys

HAN = r"[一-鿿]"

# 硬规则词：出现即错误（Blake 点名过或写进全局设定的）
BAN = ["首先", "其次", "综上所述", "值得注意的是", "不难发现", "总而言之", "说白了", "意味着什么",
       "本质上", "换句话说", "不可否认", "赋能", "底层逻辑", "闭环", "重塑", "让我们深入", "深入探讨",
       "在当今", "随着技术的", "令人发指", "历史不会重复", "总会押韵", "精妙", "划时代", "一句话讲清楚",
       "生态", "惊喜", "至关重要", "无缝", "拭目以待", "不言而喻", "毋庸置疑"]
# 软信号：出现要回看，有实际含义可以留
SOFT = {
    "这件事": "常可删掉，直接说动作",
    "极其": "夸张词别当口头禅",
    "标志着": "意义拔高，确认后面有具体内容",
    "彰显": "句尾拔高，多半可删",
    "堪称": "宣传语",
    "全新": "宣传语",
    "颠覆": "宣传语，且可能触发绝对化",
    "接下来让我们": "起跑式铺垫，删掉直接说",
    "以下是你需要知道的": "起跑式铺垫",
    "不要误会": "与假想敌辩论",
    "希望这对您有帮助": "客服腔",
    "好问题": "客服腔",
    "进行了": "进行加动词，换直接动词",
    "进行一": "进行加动词，换直接动词",
    "期待更多可能": "套话收尾",
}
# 合规相关（完整规则以 compliance_scan.py 为准，这里只提醒）
COMPLIANCE = [r"去\s*(GitHub|github|arXiv|arxiv|B站|抖音|小红书|百度|谷歌|Google)\s*(搜|找|下载)",
              r"链接在评论区", r"扣\s*1", r"最强", r"(全网|行业|国内|全球|排名|销量)第一|第一名", r"100%",
              r"吊打", r"永久免费", r"白嫖"]
TTS_BAD = [("秒", "口播里不用「秒」字"), ("划", "「划」会被念错，换「画」"), ("闯", "「闯」被念成「传」"),
           (r"\d+\s*块", "数字加「块」会读错"), (r"(?<![第\d.])2\s*(件|招|样|个|块)", "数量 2 写「两」"),
           (r"\d{3,}%", "三位数百分数写汉字念法"), (r"[A-Za-z]+\s*\d\.\d", "版本号小数读糊")]


def strip_protected(text):
    text = re.sub(r"\A---\n.*?\n---\n", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"^```.*?^```[ \t]*$", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S | re.M)
    text = re.sub(r"`[^`\n]+`", " ", text)
    text = re.sub(r"<[^>\n]+>", "", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\]\([^)\n]*\)", "]", text)
    text = re.sub(r"(~|/Users)/[^\s，。；：）」]+", " ", text)
    return text


# 2026-10-24 A026，Blake：「这种句子非常 AI，给我删掉」（点名「这句我挺认的」）
SELF_COMMENT = [
    r"(这句|这点|这条|这个)我(挺|很|还挺|真)(认|服|喜欢|认同)",
    r"这正是我(要|想要)的", r"我是真没想到", r"处理得(挺|很)(克制|到位|漂亮)",
    r"倒(是)?挺像样", r"更值得(一)?看", r"你得会看", r"我的(建议|选法|做法)很(土|简单)",
    r"我只说一句", r"有个门槛提前说", r"容易传错的事", r"比你比划半天强", r"比看跑分(实在|有用)",
    r"进步是真的", r"挺有意思的(案例|地方)", r"我觉得(最)?像人干的事", r"这版我挺喜欢",
]


def load(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        out = []
        def walk(x):
            if isinstance(x, str): out.append(x)
            elif isinstance(x, list): [walk(i) for i in x]
            elif isinstance(x, dict): [walk(v) for k, v in x.items() if k not in ("id", "scene", "file", "path")]
        walk(json.loads(raw))
        return "\n".join(out)
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--mode", choices=["article", "koubo", "subtitle"], default="article")
    a = ap.parse_args()
    text = strip_protected(load(a.path))
    err, warn = [], []

    for n, line in enumerate(text.split("\n"), 1):
        t = line.strip()
        if not t: continue
        short = t if len(t) <= 40 else t[:40] + "…"
        E = lambda msg: err.append(f"第{n}行 {msg}：{short}")
        W = lambda msg: warn.append(f"第{n}行 {msg}：{short}")

        if re.search(r"[—―]|(?<![-\w])--(?![-\w])", t): E("破折号，断句用句号，补充用全角括号")
        if re.search(r"不是[^。！？\n]{0,25}(而是|，是|，而|更是)|与其说[^。！？]{0,20}不如|不(只|仅|单)是[^。！？]{0,20}(而是|还是|更是|，(这|它|而)?是)|不仅仅?是[^。！？]{0,20}更是|而不是", t):
            E("否定对比句（不是X而是Y一类），改成正面直述，两半信息都要留")
        if re.search(HAN + r"[,;:?!]|[,;:?!]" + HAN + r"|" + HAN + r"\.(?!\d)|(?<!\d)\." + HAN, t):
            E("半角标点混进中文")
        if re.search(r"\d,\d{3}", t): E("数字千分位逗号，写 10 万或 100000")
        for w in BAN:
            if w in t: E(f"禁用词「{w}」")
        for p in SELF_COMMENT:
            if re.search(p, t): E("作者自我点评句（替读者打分或预告下一句），删掉；要留判断就写成具体事实")
        if re.search(r"长出(来|了)", t) and not re.search(r"(头发|牙|叶|芽|草|肉|毛|痘|皮)", t):
            W("「长出来」用于抽象事物时改成逐步形成、演化为")
        if re.search(r"[“”\"]", t): W("引号：引语改用「」，用来强调的直接删")
        for m in re.finditer(r"「([^」]{1,6})」", t):
            W(f"「{m.group(1)}」像是用符号强调，要强调就加粗；引语、按钮名、专名可以留")
        for w, why in SOFT.items():
            if w in t: W(f"「{w}」{why}")
        if re.search(r"随着[^，。]{1,15}的(不断)?(发展|进步|普及)", t): W("「随着……的发展」开头，背景没信息就删")
        if len(re.findall(r"的", t)) >= 5 and len(t) < 60: W("一句里「的」太多，考虑拆句")
        if re.search(r"？[^。！？\n]{1,14}[。！]", t): W("一问一答，非真悬念就直接陈述")
        for p in COMPLIANCE:
            if re.search(p, t): W(f"合规风险（{p}），发布前以 compliance_scan.py 为准")
        if a.mode == "koubo":
            for p, why in TTS_BAD:
                if re.search(p, t): W("配音风险：" + why)
            if re.search(r"(?<![一-鿿])[三四五六七八九十百千]+(个|条|次|年|天|倍|万|亿|小时|分钟)", t):
                W("数字写阿拉伯数字")
        if a.mode == "subtitle" and re.search(r"[，。；：！？、,.;:!?]", t):
            E("字幕不放标点")

    body = re.sub(r"\s", "", text)
    if len(re.findall(r"首先|第一[，、]|先说第一个", body)) and len(re.findall(r"第二[，、]|再说第二个|其次", body)) >= 1 \
            and len(re.findall(r"第三[，、]|最后[，、]", body)) >= 1:
        warn.append("全篇 第一、第二、第三 报菜名式结构，别每个点都编号")
    han = len(re.findall(HAN, body))
    print(f"模式 {a.mode}，汉字 {han}")
    for e in err: print("错误", e)
    for w in warn: print("警告", w)
    print(f"错误 {len(err)} 项，警告 {len(warn)} 项")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
