# GitHub 热门 Python 项目分析（中文）

[English Version](README_en.md)

本项目用于从 GitHub Search API 获取热门 Python 仓库数据，并生成可直接展示或发布的可视化页面与 Markdown 内容。

## 目录与文件说明

下表说明当前项目内每个主要文件的作用。

| 文件名 | 类型 | 作用 | 备注 |
|---|---|---|---|
| python_repos_visual_cn_top10.py | Python 脚本 | 拉取热门 Python 仓库数据，生成主可视化页面。 | 文件名包含 top10，但当前脚本实际生成 Top 20 页面。 |
| python_repos_category_analysis_cn.py | Python 脚本 | 按关键词对 Top 20 仓库做分类（AI、Python、Skills、编程辅助），生成分类分析页面。 | 输出包含 2x2 饼图与分类列表。 |
| python_repos_top20_blog_list_cn.py | Python 脚本 | 生成适合博客复制的 Top 20 Markdown 文本，并同时生成带复制按钮的 HTML 页面。 | 产出 md + html 两个文件。 |
| github_hot_python_top20_cn.html | HTML 页面 | 主仪表盘页面（Top 20，支持 Stars/Forks 动态切换与详情卡片）。 | 由 python_repos_visual_cn_top10.py 生成。 |
| github_hot_python_top20_category_analysis_cn.html | HTML 页面 | 分类分析页面（AI/Python/Skills/编程辅助占比）。 | 由 python_repos_category_analysis_cn.py 生成。 |
| github_hot_python_top20_blog_list.md | Markdown 文档 | Top 20 仓库清单（中英简介 + 关键指标），可直接贴到博客。 | 由 python_repos_top20_blog_list_cn.py 生成。 |
| github_hot_python_top20_blog_list.html | HTML 页面 | 包含 Markdown 文本框与一键复制按钮的页面。 | 由 python_repos_top20_blog_list_cn.py 生成。 |
| github_hot_python_top10_cn.html | HTML 页面 | 早期版本的 Top 10 展示页面。 | 静态结果文件，可保留作对比。 |
| github_stars_chart.html | HTML 页面 | 早期图表导出结果（体积较大，内含 Plotly 脚本）。 | 静态结果文件。 |
| .gitignore | 配置文件 | 忽略 Python 缓存、虚拟环境和常见编辑器临时文件。 | 版本控制辅助文件。 |

## 环境要求

- Python 3.9 或更高版本
- 可访问 GitHub API 的网络环境

## 需要安装的包

本项目运行脚本所需第三方包：

- requests
- plotly

安装命令：

```bash
pip install requests plotly
```

可选方式（先创建虚拟环境再安装）：

```bash
python -m venv .venv
# Windows
.\\.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install requests plotly
```

## 使用方式

### 1) 可选：配置 GitHub Token（推荐）

为了提升 GitHub API 请求额度，建议设置环境变量 GITHUB_TOKEN。

Windows PowerShell：

```powershell
$env:GITHUB_TOKEN = "你的token"
```

macOS/Linux：

```bash
export GITHUB_TOKEN="你的token"
```

如果不设置，也可以运行，但可能更容易触发 API 频率限制。

### 2) 运行脚本生成内容

主可视化页面：

```bash
python python_repos_visual_cn_top10.py
```

分类分析页面：

```bash
python python_repos_category_analysis_cn.py
```

博客 Markdown 与复制页：

```bash
python python_repos_top20_blog_list_cn.py
```

### 3) 打开生成文件

运行后可在当前目录直接打开：

- github_hot_python_top20_cn.html
- github_hot_python_top20_category_analysis_cn.html
- github_hot_python_top20_blog_list.html
- github_hot_python_top20_blog_list.md

## 数据来源与说明

- 数据来源：GitHub Search API
- 默认逻辑：优先抓取最近 30 天活跃且高星的 Python 仓库；若不足 20 条会回退到更宽松的高星查询
- 分类逻辑：基于仓库名称、描述、Topics、主页等文本关键词进行规则匹配

## 常见问题

1. 请求失败或超时
- 检查网络
- 稍后重试
- 使用 GITHUB_TOKEN 提升额度

2. 结果与上次不一致
- GitHub 星标、更新频率、排序会实时变化，属于正常现象

3. 脚本名与输出数量不一致
- python_repos_visual_cn_top10.py 当前实现输出 Top 20 页面，属于命名历史遗留，不影响功能
