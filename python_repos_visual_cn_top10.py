import os
import json
from html import escape
from datetime import datetime, timedelta

import plotly.express as px
import requests


def _build_headers():
    """构建 GitHub API 请求头，可选读取环境变量中的 Token。"""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_repositories():
    """获取最近较热门的 Python 仓库，优先最近 30 天活跃数据，不足时回退到全量高星。"""
    base_url = "https://api.github.com/search/repositories"
    headers = _build_headers()

    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_query = f"language:python stars:>3000 pushed:>={thirty_days_ago}"
    params = {"q": recent_query, "sort": "stars", "order": "desc", "per_page": 20}

    response = requests.get(base_url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])

    # 若最近 30 天数据不足 20 条，回退为高星排序。
    if len(items) < 20:
        fallback_query = "language:python stars:>10000"
        fallback_params = {
            "q": fallback_query,
            "sort": "stars",
            "order": "desc",
            "per_page": 20,
        }
        response = requests.get(
            base_url, headers=headers, params=fallback_params, timeout=20
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])

    return items[:20]


def _format_datetime(value):
    """将 GitHub 时间格式转为中文可读格式。"""
    if not value:
        return "未知"
    return value.replace("T", " ").replace("Z", "")


def _build_bilingual_descriptions(repo):
    """构建中英双语描述文本。"""
    owner = repo.get("owner", {}).get("login", "未知作者")
    language = repo.get("language") or "未知语言"
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    issues = repo.get("open_issues_count", 0)
    watchers = repo.get("watchers_count", 0)
    updated_at = _format_datetime(repo.get("updated_at", ""))

    en_description = repo.get("description") or "No description provided."
    cn_description = (
        f"这是一个由 {owner} 维护的开源 {language} 项目，"
        f"当前约 {stars:,} Stars、{forks:,} Forks、{watchers:,} Watchers，"
        f"开放问题 {issues:,} 个，最近更新于 {updated_at}。"
    )
    return en_description, cn_description


def _format_topics(repo):
    """格式化主题标签文本。"""
    topics = repo.get("topics") or []
    if not topics:
        return "无 / None"
    return ", ".join(topics[:8])


def _format_license(repo):
    """格式化许可证名称。"""
    license_info = repo.get("license") or {}
    spdx_id = license_info.get("spdx_id")
    name = license_info.get("name")
    if spdx_id and spdx_id != "NOASSERTION":
        return spdx_id
    if name:
        return name
    return "未声明 / Not specified"


def _build_chart_payload(repo_dicts):
    """构建图表动态切换所需的两套排序数据。"""
    entries = []
    for repo in repo_dicts:
        name = repo.get("name", "未知仓库")
        url = repo.get("html_url", "https://github.com")
        link = f"<a href='{url}' target='_blank'>{name}</a>"
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        owner = repo.get("owner", {}).get("login", "未知作者")
        en_desc, cn_desc = _build_bilingual_descriptions(repo)
        updated_at = _format_datetime(repo.get("updated_at", ""))
        hover = (
            f"作者：{owner}<br />"
            f"星标：{stars:,}<br />"
            f"Forks：{forks:,}<br />"
            f"Watchers：{repo.get('watchers_count', 0):,}<br />"
            f"Open Issues：{repo.get('open_issues_count', 0):,}<br />"
            f"主语言 / Language：{repo.get('language') or 'Unknown'}<br />"
            f"许可证 / License：{_format_license(repo)}<br />"
            f"主题 / Topics：{_format_topics(repo)}<br />"
            f"最近更新时间：{updated_at}<br />"
            f"简介 EN：{en_desc}<br />"
            f"概览 CN：{cn_desc}"
        )
        entries.append(
            {
                "link": link,
                "stars": stars,
                "forks": forks,
                "hover": hover,
            }
        )

    def _pack(metric):
        sorted_entries = sorted(entries, key=lambda item: item[metric], reverse=True)
        return {
            "x": [item["link"] for item in sorted_entries],
            "y": [item[metric] for item in sorted_entries],
            "hover": [item["hover"] for item in sorted_entries],
        }

    return {"stars": _pack("stars"), "forks": _pack("forks")}


def _build_dashboard_html(fig_html, repo_dicts, chart_payload_json):
    """拼接单页中文仪表板 HTML。"""
    cards_html = []
    for index, repo in enumerate(repo_dicts, start=1):
        owner = repo.get("owner", {}).get("login", "未知作者")
        name = repo.get("name", "未知仓库")
        repo_url = repo.get("html_url", "https://github.com")
        en_desc, cn_desc = _build_bilingual_descriptions(repo)
        star_count = repo.get("stargazers_count", 0)
        fork_count = repo.get("forks_count", 0)
        watchers = repo.get("watchers_count", 0)
        language = repo.get("language") or "Unknown"
        license_name = _format_license(repo)
        default_branch = repo.get("default_branch") or "main"
        homepage = repo.get("homepage") or ""
        topics_text = _format_topics(repo)

        card = f"""
        <div class=\"col-12 repo-item\" data-stars=\"{star_count}\" data-forks=\"{fork_count}\"> 
            <article class=\"repo-card p-4 p-md-4\">
                <div class=\"d-flex flex-wrap align-items-center justify-content-between gap-2\">
                    <h3 class=\"repo-title mb-1\"><span class=\"rank-num\">#{index}</span> <a href=\"{escape(repo_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">{escape(name)}</a></h3>
                    <span class=\"badge rank-badge metric-badge\">{star_count:,} Stars</span>
                </div>
                <p class=\"text-muted mb-3\">作者：{escape(owner)}</p>
                <p class=\"repo-desc mb-2\"><strong>简介 EN:</strong> {escape(en_desc)}</p>
                <p class=\"repo-desc repo-desc-cn mb-3\"><strong>概览 CN:</strong> {escape(cn_desc)}</p>
                <button type=\"button\" class=\"btn details-toggle mb-3\" aria-expanded=\"false\">展开详细信息</button>
                <div class=\"repo-details is-collapsed\">
                <div class=\"row g-2 repo-meta\">
                    <div class=\"col-6 col-md-3\"><span>Forks</span><strong>{fork_count:,}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>Open Issues</span><strong>{repo.get('open_issues_count', 0):,}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>Watchers</span><strong>{watchers:,}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>Language / 语言</span><strong>{escape(language)}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>License / 许可证</span><strong>{escape(license_name)}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>Default Branch</span><strong>{escape(default_branch)}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>创建时间</span><strong>{escape(_format_datetime(repo.get('created_at')))}</strong></div>
                    <div class=\"col-6 col-md-3\"><span>最近更新</span><strong>{escape(_format_datetime(repo.get('updated_at')))}</strong></div>
                    <div class=\"col-12\"><span>Topics / 主题</span><strong>{escape(topics_text)}</strong></div>
                    <div class=\"col-12\"><span>Homepage / 主页</span><strong>{escape(homepage) if homepage else '未设置 / Not set'}</strong></div>
                </div>
                </div>
            </article>
        </div>
        """
        cards_html.append(card)

    cards_section = "\n".join(cards_html)
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>GitHub 热门 Python 仓库 Top 20</title>
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\" />
    <style>
        :root {{
            --ink: #13293d;
            --ink-soft: #254e70;
            --bg: #f4f8fb;
            --card: #ffffff;
            --line: #d6e2ec;
            --accent: #1b98e0;
            --accent-2: #247ba0;
        }}

        body {{
            font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at 10% 10%, #e9f3fb 0%, transparent 40%),
                radial-gradient(circle at 90% 20%, #e3eef9 0%, transparent 32%),
                linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%);
        }}

        .page-wrap {{
            max-width: 1180px;
        }}

        .hero {{
            background: linear-gradient(120deg, #0b2545 0%, #134074 52%, #1d5b8f 100%);
            color: #fff;
            border-radius: 22px;
            box-shadow: 0 20px 44px rgba(12, 45, 77, 0.22);
        }}

        .hero h1 {{
            font-weight: 700;
            letter-spacing: 0.5px;
        }}

        .hero p {{
            color: rgba(255, 255, 255, 0.88);
            margin-bottom: 0;
        }}

        .panel {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 10px 24px rgba(18, 62, 102, 0.09);
        }}

        .repo-card {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 8px 20px rgba(28, 76, 115, 0.08);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }}

        .repo-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 14px 30px rgba(28, 76, 115, 0.14);
        }}

        .repo-title {{
            font-size: 1.15rem;
            line-height: 1.4;
            margin: 0;
        }}

        .repo-title a {{
            color: var(--ink-soft);
            text-decoration: none;
            border-bottom: 1px dashed transparent;
        }}

        .repo-title a:hover {{
            color: var(--accent-2);
            border-bottom-color: var(--accent-2);
        }}

        .repo-desc {{
            color: #2c4b66;
        }}

        .repo-desc-cn {{
            color: #1e4f74;
        }}

        .rank-badge {{
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: #fff;
            font-weight: 600;
            border-radius: 999px;
            padding: 0.45rem 0.8rem;
        }}

        .details-toggle {{
            border-radius: 999px;
            border: 1px solid #9fc3de;
            color: #12476b;
            background: #f0f8ff;
            font-weight: 600;
            padding: 0.35rem 0.85rem;
        }}

        .details-toggle:hover {{
            color: #0f3d5b;
            border-color: #7eb0d1;
            background: #e6f3ff;
        }}

        .repo-details.is-collapsed {{
            display: none;
        }}

        .repo-meta span {{
            display: block;
            color: #5d7488;
            font-size: 0.85rem;
            margin-bottom: 2px;
        }}

        .repo-meta strong {{
            font-size: 0.96rem;
            color: #1e3f5a;
        }}

        .sort-toolbar .btn-sort {{
            border-radius: 999px;
            border: 1px solid #8fb7d8;
            color: #0f3f61;
            background: #f4fbff;
            padding: 0.45rem 1rem;
            font-weight: 600;
        }}

        .sort-toolbar .btn-sort.active {{
            color: #fff;
            border-color: transparent;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
        }}

        @media (min-width: 768px) {{
            .details-toggle {{
                display: none;
            }}

            #toggle-all-details {{
                display: none;
            }}

            .repo-details.is-collapsed,
            .repo-details {{
                display: block;
            }}
        }}
    </style>
</head>
<body>
    <main class=\"container page-wrap py-4 py-md-5\">
        <section class=\"hero p-4 p-md-5 mb-4\">
            <h1 class=\"h2 mb-2\">GitHub 热门 Python 仓库 Top 20</h1>
            <p>专业交互图表 + 中英双语项目详情卡片。数据来源：GitHub Search API，生成时间：{generated_time}</p>
            <div class=\"sort-toolbar mt-3 d-flex gap-2\">
                <button id=\"sort-stars\" type=\"button\" class=\"btn btn-sort active\">按 Stars 排序</button>
                <button id=\"sort-forks\" type=\"button\" class=\"btn btn-sort\">按 Forks 排序</button>
                <button id=\"toggle-all-details\" type=\"button\" class=\"btn btn-sort\">全部展开</button>
            </div>
        </section>

        <section class=\"panel p-2 p-md-3 mb-4\">
            {fig_html}
        </section>

        <section id=\"repo-list\" class=\"row g-3\">
            {cards_section}
        </section>
    </main>

    <script id=\"chart-data\" type=\"application/json\">{chart_payload_json}</script>
    <script>
        const chartData = JSON.parse(document.getElementById("chart-data").textContent);
        const starsBtn = document.getElementById("sort-stars");
        const forksBtn = document.getElementById("sort-forks");
        const toggleAllBtn = document.getElementById("toggle-all-details");
        const repoList = document.getElementById("repo-list");
        let allExpanded = false;

        function setCardDetails(card, expand) {{
            const detailBox = card.querySelector(".repo-details");
            const button = card.querySelector(".details-toggle");
            if (!detailBox || !button) {{
                return;
            }}
            detailBox.classList.toggle("is-collapsed", !expand);
            button.setAttribute("aria-expanded", expand ? "true" : "false");
            button.textContent = expand ? "收起详细信息" : "展开详细信息";
        }}

        function updateToggleAllButton() {{
            if (!toggleAllBtn) {{
                return;
            }}
            toggleAllBtn.textContent = allExpanded ? "全部收起" : "全部展开";
        }}

        function updateButtons(mode) {{
            starsBtn.classList.toggle("active", mode === "stars");
            forksBtn.classList.toggle("active", mode === "forks");
        }}

        function updateCards(mode) {{
            const cards = Array.from(repoList.querySelectorAll(".repo-item"));
            cards.sort((a, b) => Number(b.dataset[mode]) - Number(a.dataset[mode]));
            cards.forEach((card, idx) => {{
                repoList.appendChild(card);
                const rankNode = card.querySelector(".rank-num");
                if (rankNode) {{
                    rankNode.textContent = `#${{idx + 1}}`;
                }}
                const badge = card.querySelector(".metric-badge");
                if (badge) {{
                    const value = Number(card.dataset[mode]).toLocaleString("zh-CN");
                    badge.textContent = mode === "stars" ? `${{value}} Stars` : `${{value}} Forks`;
                }}
            }});
        }}

        function updateChart(mode) {{
            const plot = document.querySelector(".js-plotly-plot");
            if (!plot || !window.Plotly) {{
                return;
            }}
            const data = chartData[mode];
            window.Plotly.restyle(
                plot,
                {{
                    x: [data.x],
                    y: [data.y],
                    text: [data.y],
                    hovertext: [data.hover],
                    "marker.color": [data.y],
                }},
                [0]
            );
            window.Plotly.relayout(plot, {{
                "yaxis.title.text": mode === "stars" ? "Star 数" : "Forks 数",
                "title.text": mode === "stars" ? "GitHub 热门 Python 仓库 Top 20（按 Stars）" : "GitHub 热门 Python 仓库 Top 20（按 Forks）",
            }});
        }}

        function applySort(mode) {{
            updateButtons(mode);
            updateCards(mode);
            updateChart(mode);
        }}

        repoList.addEventListener("click", (event) => {{
            const button = event.target.closest(".details-toggle");
            if (!button) {{
                return;
            }}

            const card = button.closest(".repo-card");
            if (!card) {{
                return;
            }}

            const detailBox = card.querySelector(".repo-details");
            if (!detailBox) {{
                return;
            }}

            const willExpand = detailBox.classList.contains("is-collapsed");
            setCardDetails(card, willExpand);
            const cards = Array.from(repoList.querySelectorAll(".repo-item .repo-card"));
            allExpanded = cards.length > 0 && cards.every((item) => !item.querySelector(".repo-details")?.classList.contains("is-collapsed"));
            updateToggleAllButton();
        }});

        toggleAllBtn.addEventListener("click", () => {{
            const targetExpand = !allExpanded;
            const cards = Array.from(repoList.querySelectorAll(".repo-item .repo-card"));
            cards.forEach((card) => setCardDetails(card, targetExpand));
            allExpanded = targetExpand;
            updateToggleAllButton();
        }});

        updateToggleAllButton();

        starsBtn.addEventListener("click", () => applySort("stars"));
        forksBtn.addEventListener("click", () => applySort("forks"));
    </script>
</body>
</html>
"""


def main():
    try:
        repo_dicts = _fetch_repositories()
    except requests.RequestException as exc:
        print(f"请求 GitHub API 失败：{exc}")
        return

    if not repo_dicts:
        print("未获取到仓库数据，请稍后重试。")
        return

    chart_payload = _build_chart_payload(repo_dicts)
    repo_links = chart_payload["stars"]["x"]
    stars = chart_payload["stars"]["y"]
    hover_texts = chart_payload["stars"]["hover"]

    title = "GitHub 热门 Python 仓库 Top 20（按 Stars）"
    labels = {"x": "仓库（可点击）", "y": "Star 数"}
    fig = px.bar(
        x=repo_links,
        y=stars,
        title=title,
        labels=labels,
        color=stars,
        color_continuous_scale=["#1f4e79", "#2e75b6", "#4f9ad7", "#7eb8e6", "#bfdcf4"],
        hover_name=hover_texts,
        text=stars,
    )

    fig.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
        marker_line_color="#174568",
        marker_line_width=1.2,
        opacity=0.9,
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
    )

    fig.update_layout(
        title_font_size=28,
        title_font_family="Microsoft YaHei",
        xaxis_title_font_size=18,
        yaxis_title_font_size=18,
        font=dict(
            family="Microsoft YaHei, SimHei, sans-serif", size=14, color="#123c5a"
        ),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f7fbff",
        margin=dict(l=80, r=50, t=90, b=140),
        coloraxis_showscale=False,
    )

    fig.update_xaxes(tickangle=-28)
    fig.update_yaxes(showgrid=True, gridcolor="#d7e6f3")

    output_file = "github_hot_python_top20_cn.html"
    fig_html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )
    chart_payload_json = json.dumps(chart_payload, ensure_ascii=False)
    page_html = _build_dashboard_html(fig_html, repo_dicts, chart_payload_json)

    with open(output_file, "w", encoding="utf-8") as file_obj:
        file_obj.write(page_html)

    print(f"图表已生成：{output_file}")


if __name__ == "__main__":
    main()
