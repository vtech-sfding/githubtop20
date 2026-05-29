import os
from datetime import datetime, timedelta
from html import escape

import plotly.graph_objects as go
import requests
from plotly.subplots import make_subplots


def build_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_top20_repositories():
    base_url = "https://api.github.com/search/repositories"
    headers = build_headers()
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    recent_query = f"language:python stars:>3000 pushed:>={thirty_days_ago}"
    params = {"q": recent_query, "sort": "stars", "order": "desc", "per_page": 20}
    response = requests.get(base_url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    items = response.json().get("items", [])

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
        items = response.json().get("items", [])

    return items[:20]


def normalize_text(repo):
    topics = repo.get("topics") or []
    content = " ".join(
        [
            repo.get("name") or "",
            repo.get("full_name") or "",
            repo.get("description") or "",
            " ".join(topics),
            repo.get("homepage") or "",
        ]
    )
    return content.lower()


def has_keywords(text, keywords):
    return any(keyword in text for keyword in keywords)


def classify_repo(repo):
    text = normalize_text(repo)

    ai_keywords = {
        "ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural",
        "transformer",
        "llm",
        "gpt",
        "nlp",
        "computer vision",
        "diffusion",
        "rag",
        "agent",
    }
    skill_keywords = {
        "skill",
        "skills",
        "learn",
        "learning",
        "tutorial",
        "guide",
        "roadmap",
        "awesome",
        "practice",
        "interview",
    }
    coding_assist_keywords = {
        "assistant",
        "copilot",
        "autocomplete",
        "code generation",
        "coding",
        "developer tool",
        "dev tool",
        "ide",
        "plugin",
        "extension",
        "lsp",
        "formatter",
        "lint",
        "debug",
        "sdk",
        "framework",
    }

    is_ai = has_keywords(text, ai_keywords)
    is_python = (repo.get("language") or "").lower() == "python" or "python" in text
    is_skills = has_keywords(text, skill_keywords)
    is_coding_assist = has_keywords(text, coding_assist_keywords)

    return {
        "ai": is_ai,
        "python": is_python,
        "skills": is_skills,
        "coding_assist": is_coding_assist,
    }


def build_category_result(repos):
    category_map = {
        "AI 项目": [],
        "Python 项目": [],
        "Skills 项目": [],
        "编程辅助项目": [],
    }

    for repo in repos:
        flags = classify_repo(repo)
        item = {
            "name": repo.get("full_name") or repo.get("name") or "unknown",
            "url": repo.get("html_url") or "https://github.com",
            "stars": repo.get("stargazers_count", 0),
            "watchers": repo.get("watchers_count", 0),
        }
        if flags["ai"]:
            category_map["AI 项目"].append(item)
        if flags["python"]:
            category_map["Python 项目"].append(item)
        if flags["skills"]:
            category_map["Skills 项目"].append(item)
        if flags["coding_assist"]:
            category_map["编程辅助项目"].append(item)

    return category_map


def build_pie_figure(category_map, total_count):
    figure = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "domain"}, {"type": "domain"}],
        ],
        subplot_titles=(
            "AI 项目占比",
            "Python 项目占比",
            "Skills 项目占比",
            "编程辅助项目占比",
        ),
    )

    charts = [
        ("AI 项目", "#2E86AB"),
        ("Python 项目", "#3BCEAC"),
        ("Skills 项目", "#FF9F1C"),
        ("编程辅助项目", "#5C4D7D"),
    ]

    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for (category, color), (row, col) in zip(charts, positions):
        matched = len(category_map[category])
        others = max(total_count - matched, 0)
        figure.add_trace(
            go.Pie(
                labels=[category, "其他项目"],
                values=[matched, others],
                hole=0.55,
                marker=dict(colors=[color, "#DCE6EF"]),
                textinfo="percent+value",
                insidetextorientation="radial",
            ),
            row=row,
            col=col,
        )

    figure.update_layout(
        title="GitHub 热门仓库 Top 20 分类占比分析",
        title_font=dict(size=28, family="Microsoft YaHei"),
        font=dict(family="Microsoft YaHei, SimHei, sans-serif", size=13),
        margin=dict(l=20, r=20, t=90, b=20),
        paper_bgcolor="#F8FBFF",
        legend=dict(orientation="h", y=-0.06, x=0.5, xanchor="center"),
    )
    return figure


def render_category_list(category_map):
    sections = []
    for category, repos in category_map.items():
        if repos:
            lines = []
            for repo in sorted(repos, key=lambda x: x["stars"], reverse=True):
                lines.append(
                    "<li>"
                    f"<a href='{escape(repo['url'])}' target='_blank' rel='noopener noreferrer'>{escape(repo['name'])}</a>"
                    f" <span class='meta'>Stars: {repo['stars']:,} | Watchers: {repo['watchers']:,}</span>"
                    "</li>"
                )
            list_html = "\n".join(lines)
        else:
            list_html = "<li>未识别到该类型项目</li>"

        section = f"""
        <section class='card'>
            <h3>{category}（{len(repos)} / 20）</h3>
            <ul>
                {list_html}
            </ul>
        </section>
        """
        sections.append(section)
    return "\n".join(sections)


def build_html_page(fig_html, category_map, repos):
    top_by_stars = sorted(
        repos, key=lambda item: item.get("stargazers_count", 0), reverse=True
    )[:3]
    top_by_watchers = sorted(
        repos, key=lambda item: item.get("watchers_count", 0), reverse=True
    )[:3]

    star_lines = "".join(
        f"<li><a href='{escape(repo.get('html_url') or 'https://github.com')}' target='_blank' rel='noopener noreferrer'>{escape(repo.get('full_name') or repo.get('name') or 'unknown')}</a>（{repo.get('stargazers_count', 0):,} Stars）</li>"
        for repo in top_by_stars
    )
    watcher_lines = "".join(
        f"<li><a href='{escape(repo.get('html_url') or 'https://github.com')}' target='_blank' rel='noopener noreferrer'>{escape(repo.get('full_name') or repo.get('name') or 'unknown')}</a>（{repo.get('watchers_count', 0):,} Watchers）</li>"
        for repo in top_by_watchers
    )

    category_html = render_category_list(category_map)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Top 20 热门项目分类分析</title>
  <style>
    :root {{
      --ink: #14263b;
      --muted: #4b647c;
      --bg: #f3f8fc;
      --card: #ffffff;
      --line: #d5e3f0;
    }}
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 8% 8%, #e5f2ff 0%, transparent 35%), var(--bg);
    }}
    .wrap {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    .hero {{
      background: linear-gradient(120deg, #0c2845, #1a4f7a);
      color: #fff;
      border-radius: 18px;
      padding: 20px 22px;
      box-shadow: 0 14px 30px rgba(17, 52, 86, 0.22);
    }}
    .hero p {{
      margin: 6px 0 0;
      color: #e8f2fb;
    }}
    .panel {{
      margin-top: 16px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 10px;
    }}
    .insights {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(2, minmax(260px, 1fr));
      gap: 12px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: 0 6px 14px rgba(16, 55, 90, 0.08);
    }}
    .card h3 {{
      margin: 0 0 8px;
      font-size: 1.03rem;
    }}
    .card ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .card li {{
      margin: 6px 0;
      line-height: 1.45;
    }}
    .card a {{
      color: #125184;
      text-decoration: none;
      border-bottom: 1px dashed transparent;
    }}
    .card a:hover {{
      border-bottom-color: #125184;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.92rem;
    }}
    @media (max-width: 860px) {{
      .insights {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>GitHub 热门项目 Top 20 分类分析</h1>
      <p>分类维度：AI 项目、Python 项目、Skills 项目、编程辅助项目（基于仓库名称、描述、Topics 的关键词识别）。</p>
      <p>生成时间：{generated_at}</p>
    </section>

    <section class="panel">
      {fig_html}
    </section>

    <section class="insights">
      <section class="card">
        <h3>最热门项目（按 Stars）</h3>
        <ul>{star_lines}</ul>
      </section>
      <section class="card">
        <h3>最受关注项目（按 Watchers）</h3>
        <ul>{watcher_lines}</ul>
      </section>
    </section>

    <section class="insights">
      {category_html}
    </section>
  </main>
</body>
</html>
"""


def main():
    try:
        repos = fetch_top20_repositories()
    except requests.RequestException as exc:
        print(f"请求 GitHub API 失败：{exc}")
        return

    if not repos:
        print("没有获取到仓库数据。")
        return

    category_map = build_category_result(repos)
    figure = build_pie_figure(category_map, total_count=len(repos))
    fig_html = figure.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )

    output_file = "github_hot_python_top20_category_analysis_cn.html"
    page_html = build_html_page(fig_html, category_map, repos)
    with open(output_file, "w", encoding="utf-8") as file_obj:
        file_obj.write(page_html)

    print(f"分析页面已生成：{output_file}")


if __name__ == "__main__":
    main()
