import os
from datetime import datetime, timedelta
from html import escape

import requests


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


def format_datetime(value):
    if not value:
        return "未知"
    return value.replace("T", " ").replace("Z", "")


def format_license(repo):
    license_info = repo.get("license") or {}
    spdx_id = license_info.get("spdx_id")
    name = license_info.get("name")
    if spdx_id and spdx_id != "NOASSERTION":
        return spdx_id
    if name:
        return name
    return "未声明 / Not specified"


def format_topics(repo):
    topics = repo.get("topics") or []
    if not topics:
        return "无 / None"
    return ", ".join(topics[:8])


def build_cn_overview(repo):
    owner = repo.get("owner", {}).get("login", "未知作者")
    language = repo.get("language") or "未知语言"
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    watchers = repo.get("watchers_count", 0)
    issues = repo.get("open_issues_count", 0)
    updated_at = format_datetime(repo.get("updated_at", ""))
    return (
        f"这是一个由 {owner} 维护的开源 {language} 项目，"
        f"当前约 {stars:,} Stars、{forks:,} Forks、{watchers:,} Watchers，"
        f"开放问题 {issues:,} 个，最近更新于 {updated_at}。"
    )


def repo_to_markdown(repo, rank):
    name = repo.get("name") or "unknown"
    url = repo.get("html_url") or "https://github.com"
    stars = repo.get("stargazers_count", 0)
    owner = repo.get("owner", {}).get("login", "未知作者")
    en_desc = repo.get("description") or "No description provided."
    cn_desc = build_cn_overview(repo)
    forks = repo.get("forks_count", 0)
    issues = repo.get("open_issues_count", 0)
    watchers = repo.get("watchers_count", 0)
    language = repo.get("language") or "Unknown"
    license_name = format_license(repo)
    default_branch = repo.get("default_branch") or "main"
    created_at = format_datetime(repo.get("created_at", ""))
    updated_at = format_datetime(repo.get("updated_at", ""))
    topics = format_topics(repo)
    homepage = repo.get("homepage") or "未设置 / Not set"

    return "\n".join(
        [
            f"### #{rank} [{name}]({url})",
            f"{stars:,} Stars",
            f"作者：{owner}",
            "",
            f"**简介 EN:** {en_desc}",
            "",
            f"**概览 CN:** {cn_desc}",
            "",
            f"- **Forks:** {forks:,}",
            f"- **Open Issues:** {issues:,}",
            f"- **Watchers:** {watchers:,}",
            f"- **Language / 语言:** {language}",
            f"- **License / 许可证:** {license_name}",
            f"- **Default Branch:** {default_branch}",
            f"- **创建时间:** {created_at}",
            f"- **最近更新:** {updated_at}",
            f"- **Topics / 主题:** {topics}",
            f"- **Homepage / 主页:** {homepage}",
        ]
    )


def build_markdown(repos):
    blocks = []
    for idx, repo in enumerate(repos, start=1):
        blocks.append(repo_to_markdown(repo, idx))
    return "\n\n---\n\n".join(blocks)


def build_html(markdown_text):
    escaped = escape(markdown_text)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Top 20 项目 Markdown 列表</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
      background: #f3f7fb;
      color: #14324f;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 22px 14px 28px;
    }}
    .hero {{
      background: linear-gradient(120deg, #0e2a46, #17507f);
      color: #fff;
      border-radius: 14px;
      padding: 16px 18px;
    }}
    .hero p {{
      margin: 6px 0 0;
      color: #e4eef9;
    }}
    .copy-area {{
      margin-top: 14px;
      background: #fff;
      border: 1px solid #cfdeed;
      border-radius: 12px;
      box-shadow: 0 8px 20px rgba(16, 52, 86, 0.08);
      overflow: hidden;
    }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px;
      background: #edf5fd;
      border-bottom: 1px solid #cfdeed;
      font-size: 14px;
    }}
    button {{
      border: 1px solid #5a8fbb;
      border-radius: 999px;
      background: #fff;
      color: #164569;
      font-weight: 600;
      padding: 6px 12px;
      cursor: pointer;
    }}
    textarea {{
      width: 100%;
      min-height: 72vh;
      border: none;
      outline: none;
      resize: vertical;
      padding: 16px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
      line-height: 1.55;
      color: #213c55;
      box-sizing: border-box;
      background: #fcfeff;
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Top 20 项目纯文字列表（Markdown）</h1>
      <p>可直接复制到博客。生成时间：{generated_at}</p>
    </section>

    <section class="copy-area">
      <div class="toolbar">
        <span>下面是纯文字 Markdown 内容，已按你需要的格式整理。</span>
        <button id="copy-btn" type="button">一键复制</button>
      </div>
      <textarea id="md-content">{escaped}</textarea>
    </section>
  </main>

  <script>
    const btn = document.getElementById("copy-btn");
    const area = document.getElementById("md-content");
    btn.addEventListener("click", async () => {{
      try {{
        await navigator.clipboard.writeText(area.value);
        btn.textContent = "复制成功";
        setTimeout(() => {{
          btn.textContent = "一键复制";
        }}, 1500);
      }} catch (error) {{
        area.select();
        document.execCommand("copy");
        btn.textContent = "已尝试复制";
        setTimeout(() => {{
          btn.textContent = "一键复制";
        }}, 1500);
      }}
    }});
  </script>
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

    markdown_text = build_markdown(repos)

    markdown_file = "github_hot_python_top20_blog_list.md"
    with open(markdown_file, "w", encoding="utf-8") as file_obj:
        file_obj.write(markdown_text)

    html_file = "github_hot_python_top20_blog_list.html"
    with open(html_file, "w", encoding="utf-8") as file_obj:
        file_obj.write(build_html(markdown_text))

    print(f"Markdown 已生成：{markdown_file}")
    print(f"HTML 已生成：{html_file}")


if __name__ == "__main__":
    main()
